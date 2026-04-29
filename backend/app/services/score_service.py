from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.score_record import ScoreRecord
from app.core.result import Result, Ok, Err
from app.core.errors import AppError, not_found
from app.schemas.score import ScoreResponse


async def get_score(db: AsyncSession, score_id: str) -> Result[ScoreResponse, AppError]:
    score = await db.get(ScoreRecord, score_id)
    if not score:
        return Err(not_found("score", score_id))
    return Ok(ScoreResponse.model_validate(score))


async def get_score_by_file(db: AsyncSession, file_id: str) -> Result[ScoreResponse, AppError]:
    result = await db.execute(
        select(ScoreRecord).where(ScoreRecord.file_id == file_id)
    )
    score = result.scalar_one_or_none()
    if not score:
        return Err(not_found("score", file_id))
    return Ok(ScoreResponse.model_validate(score))
