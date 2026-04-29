from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import engine, Base
from app.core.middleware import CorsHeadersMiddleware, RequestIdMiddleware
from app.core.logging import logger
from app.api.auth import router as auth_router
from app.api.users import router as users_router
from app.api.projects import router as projects_router
from app.api.files import router as files_router
from app.api.tasks import router as tasks_router
from app.api.scores import router as scores_router
from app.api.ws import router as ws_router

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # NOTE(gap): auto-create_all bypasses Alembic. Production must use `alembic upgrade head`.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("app.startup", version="2.0.0")
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(CorsHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(files_router, prefix="/api/v1")
app.include_router(tasks_router, prefix="/api/v1")
app.include_router(scores_router, prefix="/api/v1")
app.include_router(ws_router, prefix="/api/v1")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # NOTE(gap): does not log exception traceback in production — should use logger.exception()
    logger.error("unhandled_error", path=str(request.url), error=str(exc))
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(exc) if settings.debug else "Internal server error",
            },
        },
    )


@app.get("/api/v1/health")
async def health():
    # NOTE(gap): Redis + Celery health are hardcoded — will become live checks when infra is up.
    return {
        "ok": True,
        "data": {
            "status": "healthy",
            "version": "2.0.0",
            "checks": {
                "database": "connected",
                "redis": "not_configured",
                "celery": "not_configured",
            },
        },
    }
