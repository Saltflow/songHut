from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_record import TaskRecord
from app.models.file_record import FileRecord
from app.core.result import Result, Ok, Err
from app.core.errors import AppError, not_found, forbidden, task_exists
from app.schemas.task import TaskResponse, CreateMelodyTaskRequest, TaskParamsSchema
from app.schemas.common import PageParams, PageResponse


async def create_melody_task(
    db: AsyncSession,
    user_id: str,
    dto: CreateMelodyTaskRequest,
) -> Result[TaskResponse, AppError]:
    source_file = await db.get(FileRecord, dto.source_file_id)
    if not source_file:
        return Err(not_found("file", dto.source_file_id))

    existing = await db.execute(
        select(TaskRecord).where(
            TaskRecord.source_file_id == dto.source_file_id,
            TaskRecord.status.in_(["pending", "processing"]),
        )
    )
    if existing.scalar_one_or_none():
        return Err(task_exists())

    task = TaskRecord(
        user_id=user_id,
        project_id=dto.project_id,
        source_file_id=dto.source_file_id,
        task_type="melody",
        params=dto.params.model_dump(),
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return Ok(TaskResponse.model_validate(task))


async def create_accompaniment_task(
    db: AsyncSession,
    user_id: str,
    dto: CreateMelodyTaskRequest,
) -> Result[TaskResponse, AppError]:
    source_file = await db.get(FileRecord, dto.source_file_id)
    if not source_file:
        return Err(not_found("file", dto.source_file_id))

    existing = await db.execute(
        select(TaskRecord).where(
            TaskRecord.source_file_id == dto.source_file_id,
            TaskRecord.status.in_(["pending", "processing"]),
        )
    )
    if existing.scalar_one_or_none():
        return Err(task_exists())

    task = TaskRecord(
        user_id=user_id,
        project_id=dto.project_id,
        source_file_id=dto.source_file_id,
        task_type="accompaniment",
        params=dto.params.model_dump(),
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return Ok(TaskResponse.model_validate(task))


async def create_score_task(
    db: AsyncSession,
    user_id: str,
    source_file_id: str,
) -> Result[TaskResponse, AppError]:
    source_file = await db.get(FileRecord, source_file_id)
    if not source_file:
        return Err(not_found("file", source_file_id))

    task = TaskRecord(
        user_id=user_id,
        source_file_id=source_file_id,
        task_type="score",
        status="pending",
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return Ok(TaskResponse.model_validate(task))


async def get_task(
    db: AsyncSession, task_id: str, user_id: str,
) -> Result[TaskResponse, AppError]:
    task = await db.get(TaskRecord, task_id)
    if not task:
        return Err(not_found("task", task_id))
    if task.user_id != user_id:
        return Err(forbidden())
    return Ok(TaskResponse.model_validate(task))


async def list_tasks(
    db: AsyncSession, user_id: str, status: str | None, page: PageParams,
) -> Result[PageResponse[TaskResponse], AppError]:
    conditions = [TaskRecord.user_id == user_id]
    if status:
        conditions.append(TaskRecord.status == status)

    count_q = select(func.count(TaskRecord.id)).where(*conditions)
    total = (await db.execute(count_q)).scalar_one()

    offset = (page.page - 1) * page.page_size
    q = (
        select(TaskRecord)
        .where(*conditions)
        .order_by(TaskRecord.created_at.desc())
        .offset(offset)
        .limit(page.page_size)
    )
    tasks = (await db.execute(q)).scalars().all()

    import math
    items = [TaskResponse.model_validate(t) for t in tasks]
    return Ok(PageResponse(
        items=items,
        total=total,
        page=page.page,
        page_size=page.page_size,
        total_pages=math.ceil(total / page.page_size) if total > 0 else 1,
    ))


async def cancel_task(
    db: AsyncSession, task_id: str, user_id: str,
) -> Result[TaskResponse, AppError]:
    task = await db.get(TaskRecord, task_id)
    if not task:
        return Err(not_found("task", task_id))
    if task.user_id != user_id:
        return Err(forbidden())

    if task.status not in ("pending", "processing"):
        return Err(AppError(
            code="TASK_CANCELLED",
            message=f"Cannot cancel task in status: {task.status}",
            http_status=400,
        ))

    task.status = "cancelled"
    task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    await db.refresh(task)
    return Ok(TaskResponse.model_validate(task))


async def update_task_status(
    db: AsyncSession,
    task_id: str,
    status: str,
    progress: float = 0.0,
    error_message: str | None = None,
    result_file_id: str | None = None,
) -> Result[TaskResponse, AppError]:
    task = await db.get(TaskRecord, task_id)
    if not task:
        return Err(not_found("task", task_id))

    task.status = status
    task.progress = progress
    if error_message:
        task.error_message = error_message
    if result_file_id:
        task.result_file_id = result_file_id
    if status in ("completed", "failed", "cancelled"):
        task.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    await db.commit()
    await db.refresh(task)
    return Ok(TaskResponse.model_validate(task))
