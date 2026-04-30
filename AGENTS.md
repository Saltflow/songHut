# AGENTS.md — SongHut

> This file provides context for AI coding assistants working on the SongHut codebase.
> SongHut v2.0 is being actively refactored. See [`refactoring-plan/`](./refactoring-plan/) for design docs.

## v2.0 模块 (active development)

| 组件 | 路径 | 技术 |
|------|------|------|
| **Backend** | [`backend/`](./backend/) | FastAPI + SQLAlchemy + PostgreSQL |
| **Frontend** | [`frontend/`](./frontend/) | React + TypeScript + Vite |

- 后端验证: `cd backend && python verify.py` (32 tests, SQLite)
- 前端构建: `cd frontend && pnpm build:web`
- 部署: `docker compose up -d` (provides PostgreSQL + Redis)

## v1.0 模块 (archive, for reference only)

四独立子工程（无 monorepo 工具，无根级构建）：
- `spring后台/songhut/songhut/` — Spring Boot 后台（端口 8080）
- `django后台及音乐算法/django/songhut/` — Django 后台 + 哼唱转旋律算法（端口 8000）
- `LSTM神经网络/LSTM/` — LSTM 自动伴奏模型（TensorFlow 1.x）
- `安卓/SongHut/` — Android 客户端

## 架构关键

请求通路：Android → Spring(8080) → Django(8000, 线程内跑算法) → Spring 回调 `/api/external/completeTask`

## Spring Boot（`spring后台/songhut/songhut/`）

- **无 `pom.xml` 或 `build.gradle`** → 只能通过 IntelliJ IDEA 构建，不能从 CLI 用 Maven/Gradle 编译。
- 依赖 MyBatis 注解（无 XML mapper）、Druid 连接池、自定义 JWT。
- MySQL 数据库 `songhut`，凭据见 `util/DruidConfig.java`，`localhost:3306`。
- 文件存储 `E:/data`（Windows）或 `/home/songhut/data`（Linux）（`util/Constants.java:8`）。
- 调用 Django 的地址：`http://localhost:8000/songhut/getMelody/`（`util/Constants.java:11`）。
- CORS 过滤器：`CorsFilter.java`。
- Swagger UI：`Swagger2Config.java`。

## Django（`django后台及音乐算法/django/songhut/`）

- Django 2.1.3，Python 3.5 时代代码。
- **无 `requirements.txt`**。依赖库：django、librosa、mido、numpy、pandas、tensorflow（1.x）、midi2audio（FluidSynth）、python-osc。
- CSRF **已禁用**（`settings.py:47`）。
- 使用 SQLite（`db.sqlite3`），无 Django models。
- 环境要求：`checkpoints/` 下有 TensorFlow 检查点文件（LSTM 模型），`music/a.sf2` SoundFont 文件用于 MIDI 合成。
- 启动：`python manage.py runserver 8000`（在 `django后台及音乐算法/django/songhut/` 目录下）。

## LSTM 模型（`LSTM神经网络/LSTM/`）

- TensorFlow **1.x**（`tf.contrib.rnn`、`tf.Session`、`tf.train.Saver`）。**不能在 TF2 下运行。**
- 重要：Django 以 `from anna_lstm.model import get_neural_chord` 导入该模块。必须将 LSTM 模块在 Python 路径上设为 `anna_lstm`（可将 `LSTM神经网络/LSTM/` 重命名/软链接为 `anna_lstm`，或设置 `PYTHONPATH`）。
- 模型检查点从运行目录下的 `checkpoints/` 加载（`model.py:37` `tf.train.latest_checkpoint('checkpoints')`）。
- 训练：`python train.py`。2 层 LSTM，hidden size 256，Adam lr 0.001，60 epochs，batch 2，num_steps 8。

## Android（`安卓/SongHut/`）

- Gradle 5.1.1，Android Gradle Plugin 3.2.1，compileSdk 28，minSdk 23。
- 本地 `.jar` 依赖：`app/libs/gson-2.8.5.jar`、`okhttp-3.4.2.jar`、`okio-1.13.0.jar`。
- 构建：`./gradlew assembleDebug`（在 `安卓/SongHut/` 目录下）。

## 测试

- 该仓库中**没有实质性的测试**。Django `tests.py` 和 Android 测试类均为存根/示例。无需运行测试。
- 无 lint/format/typecheck 配置。无需检查此类问题。

## 通用注意事项

- 无 CI/CD（无 GitHub Actions、Travis、Jenkins）。**无需在 PR 中期望 CI 通过。**
- 无 pre-commit 钩子（所有 `.git/hooks/` 均为 `.sample` 默认文件）。
- 仓库在 `master` 分支上。远程仓库：`github.com:Saltflow/songHut`。
- Windows 开发环境（`E:/data` 路径、`DruidConfig.java` 中的 Windows 数据库 URL）。
- 目录名含中文（安卓 = Android，spring后台 = Spring backend，django后台及音乐算法 = Django backend & music algorithm）。
