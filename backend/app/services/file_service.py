from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_record import FileRecord
from app.models.project import Project, ProjectMember
from app.core.result import Result, Ok, Err
from app.core.errors import (
    AppError, not_found, forbidden, file_too_large, file_type_unsupported,
)
from app.core.config import get_settings
from app.schemas.project import FileResponse, UpdateFileRequest
from app.storage.protocol import StorageBackend

settings = get_settings()

SUPPORTED_AUDIO_MIMES = {
    "audio/wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/webm": ".webm",
    "audio/x-wav": ".wav",
    "audio/midi": ".mid",
    "audio/x-midi": ".mid",
}

SUPPORTED_IMAGE_MIMES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

SUPPORTED_SCORE_MIMES = {
    "application/xml": ".xml",
    "text/xml": ".xml",
    "application/vnd.recordare.musicxml": ".mxl",
    "application/vnd.recordare.musicxml+xml": ".musicxml",
}

ALL_SUPPORTED = {**SUPPORTED_AUDIO_MIMES, **SUPPORTED_IMAGE_MIMES, **SUPPORTED_SCORE_MIMES}


def _check_access(db, project_id: str, user_id: str):
    pass


async def upload_file(
    db: AsyncSession,
    storage: StorageBackend,
    user_id: str,
    project_id: str,
    file_data: bytes,
    filename: str,
    category: str,
    mime_type: str,
) -> Result[FileResponse, AppError]:
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    if len(file_data) > max_bytes:
        return Err(file_too_large(settings.max_file_size_mb))

    if mime_type not in ALL_SUPPORTED:
        return Err(file_type_unsupported(mime_type))

    project = await db.get(Project, project_id)
    if not project:
        return Err(not_found("project", project_id))

    if not project.is_public:
        member_row = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        if not member_row.scalar_one_or_none():
            return Err(forbidden())

    ext = ALL_SUPPORTED.get(mime_type, ".bin")
    today = datetime.utcnow()
    storage_path_parts = [
        category,
        str(today.year),
        f"{today.month:02d}",
        f"{uuid.uuid4().hex}{ext}",
    ]
    storage_path = "/".join(storage_path_parts)

    save_result = await storage.save(storage_path, file_data)
    match save_result:
        case Err(error):
            return Err(error)
        case Ok():
            pass

    file_record = FileRecord(
        owner_id=user_id,
        project_id=project_id,
        filename=filename,
        category=category,
        mime_type=mime_type,
        file_size=len(file_data),
        storage_path=storage_path,
    )
    db.add(file_record)
    await db.commit()
    await db.refresh(file_record)

    return Ok(FileResponse.model_validate(file_record))


async def get_file(db: AsyncSession, file_id: str) -> Result[FileResponse, AppError]:
    file_record = await db.get(FileRecord, file_id)
    if not file_record:
        return Err(not_found("file", file_id))
    return Ok(FileResponse.model_validate(file_record))


async def download_file(
    db: AsyncSession,
    storage: StorageBackend,
    file_id: str,
    user_id: str | None,
) -> Result[tuple[str, bytes], AppError]:
    file_record = await db.get(FileRecord, file_id)
    if not file_record:
        return Err(not_found("file", file_id))

    if file_record.project_id and user_id:
        project = await db.get(Project, file_record.project_id)
        if project and not project.is_public:
            member_row = await db.execute(
                select(ProjectMember).where(
                    ProjectMember.project_id == file_record.project_id,
                    ProjectMember.user_id == user_id,
                )
            )
            if not member_row.scalar_one_or_none():
                return Err(forbidden())

    load_result = await storage.load(file_record.storage_path)
    match load_result:
        case Err(error):
            return Err(error)
        case Ok(data):
            return Ok((file_record.filename, data))


async def delete_file(
    db: AsyncSession,
    storage: StorageBackend,
    file_id: str,
    user_id: str,
) -> Result[None, AppError]:
    file_record = await db.get(FileRecord, file_id)
    if not file_record:
        return Err(not_found("file", file_id))

    if file_record.owner_id != user_id:
        return Err(forbidden("Only the file owner can delete this file"))

    await storage.delete(file_record.storage_path)
    await db.delete(file_record)
    await db.commit()
    return Ok(None)


async def update_file(
    db: AsyncSession, file_id: str, user_id: str, dto: UpdateFileRequest,
) -> Result[FileResponse, AppError]:
    file_record = await db.get(FileRecord, file_id)
    if not file_record:
        return Err(not_found("file", file_id))

    if file_record.owner_id != user_id:
        return Err(forbidden())

    if dto.category is not None:
        file_record.category = dto.category
    if dto.is_featured is not None:
        file_record.is_featured = dto.is_featured
    if dto.metadata is not None:
        file_record.extra_meta = {**file_record.extra_meta, **dto.metadata}

    await db.commit()
    await db.refresh(file_record)
    return Ok(FileResponse.model_validate(file_record))
