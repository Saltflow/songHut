# Contributing to SongHut

## 开发环境

```bash
git clone https://github.com/saltflow/songHut
cd songHut

# 后端
cd backend && pip install -e ".[dev]"

# 前端
cd ../frontend && pnpm install
```

## Commit 规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <subject>

type:
  feat      — 新功能
  fix       — Bug 修复
  docs      — 文档
  chore     — 工程/构建
  refactor  — 重构 (无功能变更)
  test      — 测试

scope:
  backend   — 后端
  frontend  — 前端
  algo      — 算法
  docs      — 文档

示例:
  feat(backend): add humming-to-melody pipeline
  fix(frontend): AuthGuard redirect on expired token
  docs(readme): update quick-start instructions
```

## 代码风格

### Python (后端)

```bash
cd backend
ruff check app/            # lint
mypy app/                  # 类型检查
python verify.py           # 端到端验证 (32 tests)
```

- 所有 Service 函数返回 `Result[Output, AppError]`
- 禁止 Service 层直接操作 SQLAlchemy Session 以外的 I/O
- 新端点必须通过 `TODO(verify): needs PG + uvicorn` 标记未验证的桩

### TypeScript (前端)

```bash
cd frontend
pnpm typecheck             # tsc --noEmit
pnpm build:web             # Vite 构建
```

## Pull Request 流程

1. Fork 仓库
2. 创建 feature 分支：`git checkout -b feat/xxx`  
3. 开发 + 自测
4. **运行验证**：
   - 后端：`cd backend && python verify.py`
   - 前端：`cd frontend && pnpm build:web`
5. 提交 PR，描述变更
6. 等待 Review

## 报告 Bug

使用 [Issue 模板](./.github/ISSUE_TEMPLATE/bug_report.md) 提交。
