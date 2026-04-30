# SongHut Backend

FastAPI + SQLAlchemy + PostgreSQL (开发态兼容 SQLite)

## 快速开始

```bash
cd backend
cp .env.example .env        # 编辑 SECRET_KEY 和 JWT_SECRET
pip install -e .            # 安装依赖
uvicorn app.main:app --reload --port 8000
```

无需 PostgreSQL 的快速验证：
```bash
python verify.py             # 32/32 end-to-end tests
```

## 接口文档

启动后打开 http://localhost:8000/docs — 自动生成的 Swagger UI。

## 目录结构

```
backend/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── core/                # 配置、安全、Result、日志
│   ├── models/              # SQLAlchemy ORM (7 表)
│   ├── schemas/             # Pydantic DTO
│   ├── api/                 # REST 路由 (26 端点)
│   ├── services/            # 业务逻辑 (纯函数)
│   ├── storage/             # 文件存储抽象
│   ├── algorithms/          # 算法 Pipeline (待实施)
│   └── workers/             # Celery (待实施)
├── alembic/                 # 数据库迁移
├── verify.py                # 端到端验证脚本
└── pyproject.toml
```

## 开发

```bash
ruff check app/              # lint
mypy app/                    # 类型检查
python verify.py             # 验证
```
