# Changelog

All notable changes to SongHut will be documented in this file.

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/).  
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/).

---

## [Unreleased] — v2.0.0-pre

### Added
- **后端**: FastAPI 重构，替代 Spring Boot + Django
  - 7 张数据表 (SQLAlchemy ORM)：users, projects, project_members, files, tasks, scores
  - 26 个 REST 端点 (auth, users, projects, files, tasks, scores, ws, health)
  - Bcrypt 密码哈希 + 标准 JWT 认证
  - `Result[T, E]` 函数式错误处理
  - 文件存储抽象层 (LocalStorage + S3 协议)
  - 跨数据库支持 (SQLite dev / PostgreSQL prod)
  - 32 条端到端测试 (`verify.py`)
- **前端**: React SPA，替代 Android 原生
  - pnpm workspace 三包结构 (shared + web + app)
  - Axios API 客户端 + 自动 token 刷新拦截器
  - Zustand 状态管理 (auth + project stores)
  - 5 个页面：登录/注册/仪表盘/项目详情/录音
  - Tailwind CSS 响应式布局
  - useAudioRecorder hook (Web Audio API + MediaRecorder)
  - 跨端平台检测 (`lib/platform.ts`)
- **设计文档**: 9 篇重构计划 (`refactoring-plan/`)
  - 架构概览 (C4 模型 + ADR)
  - 数据模型约定 (Pydantic frozen DTO + TypeScript types)
  - API 契约 (完整 REST + WebSocket 规范)
  - 算法 Pipeline 设计 (部署约束: 2C8G 无 GPU Linux)
  - 前端架构 + 跨端方案 + 乐谱渲染方案
  - 部署与工程化 (Docker Compose + GitHub Actions CI/CD)
- **工程化**
  - 根目录 `.gitignore` (Python + Node + IDE + OS)
  - `AGENTS.md` (AI 助手指南)
  - AGPL v3 License
  - `.github/` Issue + PR 模板

### Changed
- 数据库: MySQL → PostgreSQL 16 (开发态兼容 SQLite)
- 后端语言: Java (Spring Boot) → Python 3.12 (FastAPI)
- 前端: Android (Java) → React + TypeScript + Vite
- 认证: 手写 MD5 JWT → 标准 bcrypt + python-jose HS256

### Removed
- 旧版 LSTM 和弦预测模型 (TF1) — 替换为规则引擎
- 旧版 librosa chroma_cqt 音高检测 — 替换为 librosa.pyin

### Planned (未实施)
- 算法 Pipeline 代码实现
- Celery Worker 异步任务处理
- Redis 缓存与限流
- MinIO/S3 存储后端
- Electron 桌面壳
- VexFlow 乐谱渲染
