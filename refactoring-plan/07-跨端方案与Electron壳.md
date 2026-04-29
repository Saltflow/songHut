# SongHut 2.0 — 跨端方案与 Electron 壳

## 1. 跨端代码策略

```
┌─────────────────────────────────────────────────────────────┐
│                      shared/ (95%)                         │
│  API 客户端 · Zustand 状态 · React 组件 · 路由 · Hooks    │
│  平台抽象层 (platform.ts)                                   │
└─────────────────────────────────────────────────────────────┘
         ▲                          ▲
         │ (vite resolve alias)     │ (vite resolve alias)
         │                          │
┌────────┴──────────┐    ┌─────────┴─────────┐
│    app/ (5%)      │    │   web/ (0.5%)     │
│  Electron 主进程   │    │  PWA manifest     │
│  preload 脚本     │    │  index.html       │
│  IPC handlers     │    │  vite.config.ts   │
│  electron-builder │    └───────────────────┘
│  配置              │
└───────────────────┘

构建命令:
  pnpm build:web      → 构建 Web SPA (dist/web/)
  pnpm build:desktop  → 构建 Electron 桌面 (dist/app/)
  pnpm dev:web        → 开发 Web (Vite HMR)
  pnpm dev:desktop    → 开发桌面 (Vite HMR + Electron)
```

## 2. Electron 壳 (packages/app/)

### 2.1 主进程

```typescript
// packages/app/src/main/index.ts
import { app, BrowserWindow, ipcMain, dialog, Menu, Tray } from 'electron';
import path from 'path';
import fs from 'fs/promises';
import { registerFileHandlers } from './ipc-handlers';
import { createMenu } from './menu';
import { setupAutoUpdater } from './updater';

let mainWindow: BrowserWindow | null = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',  // macOS 融合标题栏
    trafficLightPosition: { x: 12, y: 12 },
    webPreferences: {
      preload: path.join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
    backgroundColor: '#f8f9fa',
    show: false,
  });

  // 开发模式加载 Vite dev server
  if (process.env.VITE_DEV_SERVER_URL) {
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL);
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '../../dist/index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ==== 应用生命周期 ====
app.whenReady().then(() => {
  createWindow();
  registerFileHandlers();   // 注册文件 IPC
  createMenu();             // 原生菜单
  setupAutoUpdater();       // 自动更新

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
```

### 2.2 IPC 处理程序

```typescript
// packages/app/src/main/ipc-handlers.ts
import { ipcMain, dialog } from 'electron';
import fs from 'fs/promises';
import path from 'path';

export function registerFileHandlers() {
  // 打开文件对话框
  ipcMain.handle('dialog:openFile', async (_event, options?: {
    accept?: string; multiple?: boolean;
  }) => {
    const result = await dialog.showOpenDialog({
      properties: [
        'openFile',
        ...(options?.multiple ? ['multiSelections' as const] : []),
      ],
      filters: options?.accept
        ? [{ name: 'All Files', extensions: options.accept.split(',') }]
        : [{ name: 'Audio', extensions: ['wav', 'mp3', 'm4a', 'mid'] }],
    });
    return result.canceled ? null : result.filePaths;
  });

  // 保存文件对话框
  ipcMain.handle('dialog:saveFile', async (_event, defaultName: string) => {
    const result = await dialog.showSaveDialog({
      defaultPath: defaultName,
      filters: [
        { name: 'MIDI', extensions: ['mid'] },
        { name: 'MusicXML', extensions: ['xml'] },
        { name: 'PDF', extensions: ['pdf'] },
        { name: 'WAV', extensions: ['wav'] },
      ],
    });
    return result.canceled ? null : result.filePath;
  });

  // 读取文件内容
  ipcMain.handle('file:read', async (_event, filePath: string) => {
    const buffer = await fs.readFile(filePath);
    return buffer.buffer;  // ArrayBuffer
  });

  // 写入文件
  ipcMain.handle('file:write', async (_event, filePath: string, data: ArrayBuffer) => {
    await fs.writeFile(filePath, Buffer.from(data));
  });

  // 保存 Blob 到文件 (用于 audio blob, canvas png 等)
  ipcMain.handle('file:saveBlob', async (_event, defaultName: string, data: ArrayBuffer) => {
    const filePath = await dialog.showSaveDialog({
      defaultPath: defaultName,
    });
    if (!filePath.canceled && filePath.filePath) {
      await fs.writeFile(filePath.filePath, Buffer.from(data));
      return filePath.filePath;
    }
    return null;
  });

  // 获取应用程序数据路径
  ipcMain.handle('app:getPath', (_event, name: string) => {
    const { app } = require('electron');
    return app.getPath(name as any);
  });

  // 注册/注销全局快捷键
  const shortcuts = new Map<string, () => void>();
  const { globalShortcut } = require('electron');

  ipcMain.handle('shortcut:register', (_event, key: string) => {
    globalShortcut.register(key, () => {
      mainWindow?.webContents.send('shortcut:triggered', key);
    });
  });

  ipcMain.handle('shortcut:unregister', (_event, key: string) => {
    globalShortcut.unregister(key);
  });
}
```

### 2.3 Preload 脚本

```typescript
// packages/app/src/preload/index.ts
import { contextBridge, ipcRenderer } from 'electron';

/**
 * 通过 contextBridge 安全暴露 API 给渲染进程。
 * 渲染进程通过 window.electronAPI 访问。
 */
contextBridge.exposeInMainWorld('electronAPI', {
  // 文件对话框
  openFileDialog: (options?: { accept?: string; multiple?: boolean }) =>
    ipcRenderer.invoke('dialog:openFile', options),

  saveFileDialog: (defaultName: string) =>
    ipcRenderer.invoke('dialog:saveFile', defaultName),

  // 文件读写
  readFile: (filePath: string) =>
    ipcRenderer.invoke('file:read', filePath),

  writeFile: (filePath: string, data: ArrayBuffer) =>
    ipcRenderer.invoke('file:write', filePath, data),

  saveBlob: (defaultName: string, data: ArrayBuffer) =>
    ipcRenderer.invoke('file:saveBlob', defaultName, data),

  // 应用路径
  getPath: (name: string) =>
    ipcRenderer.invoke('app:getPath', name),

  // 全局快捷键
  registerShortcut: (key: string) =>
    ipcRenderer.invoke('shortcut:register', key),

  unregisterShortcut: (key: string) =>
    ipcRenderer.invoke('shortcut:unregister', key),

  // 监听快捷键触发
  onShortcutTriggered: (callback: (key: string) => void) => {
    ipcRenderer.on('shortcut:triggered', (_event, key) => callback(key));
  },

  // 平台信息
  platform: process.platform,  // 'darwin' | 'win32' | 'linux'
  versions: {
    node: process.versions.node,
    chrome: process.versions.chrome,
    electron: process.versions.electron,
  },
});
```

### 2.4 原生菜单

```typescript
// packages/app/src/main/menu.ts
import { Menu, app, BrowserWindow } from 'electron';

export function createMenu() {
  const isMac = process.platform === 'darwin';

  const template: Electron.MenuItemConstructorOptions[] = [
    ...(isMac ? [{
      label: app.name,
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    }] : []),
    {
      label: '文件',
      submenu: [
        {
          label: '打开文件...',
          accelerator: 'CmdOrCtrl+O',
          click: () => {
            BrowserWindow.getFocusedWindow()?.webContents.send('menu:openFile');
          },
        },
        {
          label: '保存乐谱...',
          accelerator: 'CmdOrCtrl+S',
          click: () => {
            BrowserWindow.getFocusedWindow()?.webContents.send('menu:saveScore');
          },
        },
        { type: 'separator' },
        { role: isMac ? 'close' : 'quit' },
      ],
    },
    {
      label: '编辑',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
      ],
    },
    {
      label: '视图',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: '窗口',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        ...(isMac ? [
          { type: 'separator' },
          { role: 'front' },
        ] : [{ role: 'close' }]),
      ],
    },
    {
      label: '帮助',
      submenu: [
        {
          label: '关于 SongHut',
          click: () => {
            // 打开关于页面
          },
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}
```

### 2.5 Electron Builder 配置

```yaml
# packages/app/electron-builder.yml
appId: com.songhut.app
productName: SongHut
copyright: Copyright © 2024 SongHut

directories:
  output: release
  buildResources: build

files:
  - dist/**/*
  - "!node_modules/**/*"

win:
  target:
    - target: nsis
      arch: [x64, arm64]
  icon: build/icon.ico
  artifactName: ${productName}-${version}-${arch}.${ext}

nsis:
  oneClick: false
  perMachine: false
  allowToChangeInstallationDirectory: true
  deleteAppDataOnUninstall: false

mac:
  target:
    - target: dmg
      arch: [x64, arm64]
  icon: build/icon.icns
  category: public.app-category.music
  hardenedRuntime: true
  entitlements: build/entitlements.mac.plist
  extendInfo:
    NSMicrophoneUsageDescription: SongHut 需要麦克风权限来录制哼唱
    NSFolderUsageDescription: SongHut 需要文件访问权限来保存乐谱和音频

dmg:
  contents:
    - x: 130
      y: 220
    - x: 410
      y: 220
      type: link
      path: /Applications

linux:
  target:
    - target: AppImage
      arch: [x64]
    - target: deb
      arch: [x64]
  icon: build/icons
  category: Audio

publish:
  provider: github
  owner: songhut
  repo: songhut-releases

# 自动更新
autoUpdater:
  provider: github
  owner: songhut
  repo: songhut-releases
```

### 2.6 自动更新

```typescript
// packages/app/src/main/updater.ts
import { autoUpdater } from 'electron-updater';
import { BrowserWindow } from 'electron';

export function setupAutoUpdater() {
  autoUpdater.autoDownload = false;
  autoUpdater.autoInstallOnAppQuit = true;

  // 检查更新 (应用启动后延时 30 秒)
  setTimeout(() => {
    autoUpdater.checkForUpdates().catch(() => {
      /* 静默: 无更新时不做处理 */
    });
  }, 30_000);

  autoUpdater.on('update-available', (info) => {
    const win = BrowserWindow.getFocusedWindow();
    win?.webContents.send('update:available', {
      version: info.version,
      releaseDate: info.releaseDate,
    });
  });

  autoUpdater.on('download-progress', (progress) => {
    const win = BrowserWindow.getFocusedWindow();
    win?.webContents.send('update:progress', {
      percent: progress.percent,
      bytesPerSecond: progress.bytesPerSecond,
    });
  });

  autoUpdater.on('update-downloaded', () => {
    const win = BrowserWindow.getFocusedWindow();
    win?.webContents.send('update:downloaded');
  });

  // IPC: 触发下载和安装
  ipcMain.handle('update:download', () => {
    autoUpdater.downloadUpdate();
  });

  ipcMain.handle('update:install', () => {
    autoUpdater.quitAndInstall();
  });
}
```

## 3. Web 壳 (packages/web/)

```typescript
// packages/web/src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from '@songhut/shared/App';
import '@songhut/shared/styles.css';

// PWA 注册
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js');
  });
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

```html
<!-- packages/web/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="theme-color" content="#1a1a2e" />
  <link rel="manifest" href="/manifest.json" />
  <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
  <title>SongHut</title>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="/src/main.tsx"></script>
</body>
</html>
```

```json
// packages/web/public/manifest.json
{
  "name": "SongHut",
  "short_name": "SongHut",
  "description": "哼唱转旋律 · AI 音乐创作平台",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#1a1a2e",
  "theme_color": "#1a1a2e",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

## 4. 平台差异矩阵

```typescript
// shared/src/lib/platform.ts — 已有的 platform 对象
// 差异汇总:

export interface PlatformCapabilities {
  /** 系统原生对话框 */
  nativeDialogs: boolean;
  /** 全局快捷键 */
  globalShortcuts: boolean;
  /** 系统托盘 */
  systemTray: boolean;
  /** 任务栏进度 */
  taskbarProgress: boolean;
  /** 任意文件路径读写 */
  arbitraryFileAccess: boolean;
  /** 后台运行 (关闭窗口后继续) */
  backgroundRun: boolean;
  /** 离线存储 (本地数据库) */
  localDatabase: boolean;
  /** WebRTC 低延迟录音 */
  lowLatencyRecording: boolean;
}

export const capabilities: PlatformCapabilities = {
  nativeDialogs: platform.isElectron,
  globalShortcuts: platform.isElectron,
  systemTray: platform.isElectron,
  taskbarProgress: platform.isElectron,
  arbitraryFileAccess: platform.isElectron,
  backgroundRun: platform.isElectron,
  localDatabase: platform.isElectron,  // Web 端用 IndexedDB 也可实现
  lowLatencyRecording: !platform.isMobile,
};
```

### 跨端差异处理模式

```typescript
// 模式 1: 抽象层 + 策略模式
function getFilePicker(): FilePickerStrategy {
  if (platform.isElectron) {
    return new ElectronFilePicker();
  }
  return new WebFilePicker();
}

// 模式 2: 条件编译 (Vite define)
if (__ELECTRON__) {
  // Electron 特有代码 — 构建时会被 tree-shake 掉
}

// 模式 3: React 条件渲染
export function RecordButton() {
  if (platform.isElectron) {
    return <button onClick={handleNativeRecording}>录音</button>;
  }
  return <button onClick={handleWebRecording}>录音 (浏览器)</button>;
}
```

## 5. 构建配置

```typescript
// packages/shared/vite.config.ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  build: {
    lib: {
      entry: 'src/index.ts',
      formats: ['es'],
    },
    rollupOptions: {
      external: ['react', 'react-dom', 'react-router-dom'],
    },
  },
});
```

```typescript
// packages/app/vite.config.ts (Electron)
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import electron from 'vite-plugin-electron';

export default defineConfig({
  plugins: [
    react(),
    electron([
      { entry: 'src/main/index.ts' },
      { entry: 'src/preload/index.ts', onstart(args) { args.reload(); } },
    ]),
  ],
  resolve: {
    alias: {
      '@songhut/shared': path.resolve(__dirname, '../shared/src'),
    },
  },
  build: {
    outDir: 'dist',
  },
});
```

```typescript
// packages/web/vite.config.ts (Web PWA)
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg'],
      manifest: {
        name: 'SongHut',
        short_name: 'SongHut',
        start_url: '/',
        display: 'standalone',
      },
    }),
  ],
  resolve: {
    alias: {
      '@songhut/shared': path.resolve(__dirname, '../shared/src'),
    },
  },
});
```

## 6. 快捷键方案

| 快捷键 | 功能 | 平台 |
|--------|------|------|
| `Ctrl+N` | 新建项目 | Electron + Web |
| `Ctrl+O` | 打开文件 | Electron |
| `Ctrl+S` | 保存乐谱 | Electron |
| `Ctrl+R` | 开始/停止录音 | Electron + Web |
| `Space` | 播放/暂停 | Electron + Web |
| `Ctrl+Z` | 撤销 (乐谱编辑) | Electron + Web |
| `Ctrl+Shift+Z` | 重做 | Electron + Web |
| `+` `-` | 乐谱缩放 | Electron + Web |
| `Ctrl+P` | 打印/导出 PDF | Electron + Web |
| `Ctrl+,` | 打开设置 | Electron + Web |

## 7. 窗口大小及响应式断点

```css
/* Tailwind 自定义断点 */
/* sm: 640px (手机横屏/小平板) */
/* md: 768px (平板) */
/* lg: 1024px (桌面) */
/* xl: 1280px (大桌面) */

/* 桌面端默认窗口: 1280x800 */
/* 最小窗口: 960x600 */

/* Web 端自适应: 小屏隐藏侧边栏，大屏显示侧边栏 */
```

## 8. 发布流程

```
1. pnpm build:shared   — 构建共享包
2. pnpm build:web      — 构建 Web SPA (部署到 Vercel/Netlify)
3. pnpm build:desktop  — 构建 Electron (Windows: NSIS, macOS: DMG, Linux: AppImage)
4. GitHub Release      — 自动发布 + 更新推送
```
