# SongHut Frontend

React 18 + TypeScript + Vite · pnpm workspace

## 快速开始

```bash
cd frontend
pnpm install
pnpm dev:web
# 浏览器打开 http://localhost:5173
```

## 构建

```bash
pnpm build:web               # tsc --noEmit + Vite bundle
```

## 目录结构

```
frontend/
├── packages/
│   ├── shared/              # 共享代码 (API、stores、hooks、页面)
│   │   └── src/
│   │       ├── api/          # Axios 客户端 + 类型
│   │       ├── stores/       # Zustand (auth, project)
│   │       ├── hooks/        # useAuth, useProjects, useAudioRecorder
│   │       ├── features/     # 页面 (Login, Register, Dashboard, Project, Record)
│   │       ├── lib/          # 工具 (platform.ts)
│   │       └── styles/       # Tailwind CSS
│   └── web/                 # Web SPA 入口 (Vite + PWA)
│       └── src/
│           └── main.tsx
├── pnpm-workspace.yaml
└── package.json
```

## 开发

```bash
pnpm typecheck               # tsc --noEmit
pnpm build:web               # 构建验证
```
