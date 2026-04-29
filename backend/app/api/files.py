from __future__ import annotations

import io

from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_id, get_optional_user_id, get_db_session
from app.core.result import Ok, Err
from app.core.respond import respond
from app.core.logging import logger
from app.schemas.project import UpdateFileRequest
from app.services.file_service import (
    upload_file, get_file, download_file, delete_file, update_file,
)
from app.storage.factory import get_storage

router = APIRouter(tags=["files"], redirect_slashes=False)


@router.post("/projects/{project_id}/files", status_code=201)
async def upload(
    project_id: str,
    file: UploadFile = File(...),
    category: str = Form("recording"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    storage = get_storage()
    content = await file.read()
    mime_type = file.content_type or "application/octet-stream"
    filename = file.filename or "untitled"
    logger.info("file.upload", filename=filename, size=len(content), category=category)
    return respond(await upload_file(
        db, storage, user_id, project_id, content, filename, category, mime_type,
    ))


@router.get("/files/{file_id}")
async def get_metadata(
    file_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await get_file(db, file_id))


@router.get("/files/{file_id}/download")
async def download(
    file_id: str,
    user_id: str | None = Depends(get_optional_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    storage = get_storage()
    result = await download_file(db, storage, file_id, user_id)
    match result:
        case Ok(value):
            filename, data = value[0], value[1]
            return StreamingResponse(
                io.BytesIO(data),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{filename}"'},
            )
        case Err(error):
            return respond(result)


@router.delete("/files/{file_id}")
async def delete(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    storage = get_storage()
    return respond(await delete_file(db, storage, file_id, user_id))


@router.patch("/files/{file_id}")
async def update(
    file_id: str,
    body: UpdateFileRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await update_file(db, file_id, user_id, body))


@router.post("/files/{file_id}/feature")
async def set_featured(
    file_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await update_file(db, file_id, user_id, UpdateFileRequest(is_featured=True)))
