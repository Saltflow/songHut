# 🎵 SongHut 2.0

> 哼唱转旋律 · AI 音乐创作平台 — 对着手机哼一段，自动生成 MIDI 旋律+伴奏+乐谱。

[![License](https://img.shields.io/badge/license-AGPL--3.0-blue)](./LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://python.org)
[![Node](https://img.shields.io/badge/node-18+-green)](https://nodejs.org)
[![backend verify](https://img.shields.io/badge/verify-32%2F32-green)](./backend/verify.py)
[![frontend build](https://img.shields.io/badge/build-passing-brightgreen)](./frontend)

---

## 项目状态

**SongHut 2.0 正在重构中**（2026 Q2）。以下是当前进展：

| 组件 | 状态 | 说明 |
|------|------|------|
| **后端** (FastAPI) | ✅ 核心可用 | 7 表、26 端点、32 测试全绿 |
| **前端** (React Web) | ✅ 核心可用 | 5 页面、登录/注册/项目 CRUD/录音 |
| **算法** (音高检测) | 📋 设计完成 | 文档就绪，代码待实施 |
| **Electron 壳** | ⏳ 待实施 | Web 端可先用 |
| **旧版代码** (v1) | 📦 归档 | `安卓/` `spring后台/` `django后台及音乐算法/` `LSTM神经网络/` |

---

## 架构

```
┌──────────────┐     ┌──────────────────┐     ┌───────────┐
│  React SPA   │────▶│  FastAPI (8000)   │────▶│ PostgreSQL │
│  (Electron   │     │  ┌────────────┐   │     └───────────┘
│   壳可选)    │     │  │ Algorithm  │   │     ┌───────────┐
└──────────────┘     │  │ Pipeline   │   │────▶│   Redis   │
                     │  └────────────┘   │     └───────────┘
                     └──────────────────┘
```

详细架构：见 [`refactoring-plan/`](./refactoring-plan/) 设计文档。

---

## 快速开始

### 前置依赖

- **Python 3.12+** + pip
- **Node.js 18+** + pnpm (`npm i -g pnpm`)
- **PostgreSQL 16** (生产) 或 SQLite (开发测试)

### 后端

```bash
cd backend
cp .env.example .env          # 编辑 SECRET_KEY 和 JWT_SECRET
pip install -e .
uvicorn app.main:app --reload --port 8000
# 浏览器打开 http://localhost:8000/docs — Swagger UI
```

验证（无需 PostgreSQL）：
```bash
python verify.py    # 32/32 tests, 纯 SQLite
```

### 前端

```bash
cd frontend
pnpm install
pnpm dev:web
# 浏览器打开 http://localhost:5173
```

### Docker (一键起 PostgreSQL + Redis)

```bash
docker compose up -d
# 然后按上面步骤启动后端和前端
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| **后端框架** | FastAPI (Python 3.12) |
| **数据库** | PostgreSQL 16 + SQLAlchemy 2.0 |
| **任务队列** | Celery + Redis (规划中) |
| **前端框架** | React 18 + TypeScript |
| **构建工具** | Vite 6 |
| **状态管理** | Zustand |
| **样式** | Tailwind CSS 3 |
| **桌面壳** | Electron 33 (规划中) |
| **音高检测** | librosa.pyin / torchcrepe (规划中) |
| **乐谱渲染** | VexFlow 5 (规划中) |

---

## 文档索引

| 文档 | 面向 |
|------|------|
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | 如何参与开发 |
| [`CHANGELOG.md`](./CHANGELOG.md) | 版本记录 |
| [`AGENTS.md`](./AGENTS.md) | AI 编码助手指南 |
| [`refactoring-plan/`](./refactoring-plan/) | v2.0 重构设计文档 (9 篇) |

---

## 许可

[GNU Affero General Public License v3.0](./LICENSE)

Copyright © 2024–2026 SongHut Contributors
