from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_id, get_db_session
from app.core.respond import respond
from app.core.logging import logger
from app.schemas.task import (
    CreateMelodyTaskRequest,
    CreateAccompanimentTaskRequest,
    CreateScoreTaskRequest,
)
from app.schemas.common import PageParams
from app.services.task_service import (
    create_melody_task,
    create_accompaniment_task,
    create_score_task,
    get_task,
    list_tasks,
    cancel_task,
)

router = APIRouter(prefix="/tasks", tags=["tasks"], redirect_slashes=False)


@router.post("/melody", status_code=201)
async def melody(
    body: CreateMelodyTaskRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    logger.info("task.create.melody", source_id=body.source_file_id)
    return respond(await create_melody_task(db, user_id, body))


@router.post("/accompaniment", status_code=201)
async def accompaniment(
    body: CreateAccompanimentTaskRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await create_accompaniment_task(db, user_id, body))


@router.post("/score", status_code=201)
async def score(
    body: CreateScoreTaskRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await create_score_task(db, user_id, body.source_file_id))


@router.get("/{task_id}")
async def get_one(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await get_task(db, task_id, user_id))


@router.get("/")
async def get_all(
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    params = PageParams(page=page, page_size=page_size)
    return respond(await list_tasks(db, user_id, status, params))


@router.post("/{task_id}/cancel")
async def cancel(
    task_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await cancel_task(db, task_id, user_id))
