from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_id, get_db_session
from app.core.respond import respond
from app.core.logging import logger
from app.schemas.project import (
    CreateProjectRequest,
    UpdateProjectRequest,
    AddMemberRequest,
)
from app.schemas.common import PageParams
from app.services.project_service import (
    list_projects,
    create_project,
    get_project_detail,
    update_project,
    delete_project,
    add_project_member,
    remove_project_member,
)

router = APIRouter(prefix="/projects", tags=["projects"], redirect_slashes=False)


@router.get("/")
async def get_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    params = PageParams(page=page, page_size=page_size)
    return respond(await list_projects(db, user_id, params))


@router.post("/", status_code=201)
async def create(
    body: CreateProjectRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await create_project(db, user_id, body))


@router.get("/{project_id}")
async def get_detail(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    logger.debug("project.detail", project_id=project_id)
    return respond(await get_project_detail(db, project_id, user_id))


@router.patch("/{project_id}")
async def update(
    project_id: str,
    body: UpdateProjectRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await update_project(db, project_id, user_id, body))


@router.delete("/{project_id}")
async def delete(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await delete_project(db, project_id, user_id))


@router.post("/{project_id}/members", status_code=201)
async def add_member(
    project_id: str,
    body: AddMemberRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await add_project_member(db, project_id, user_id, body.user_id, body.role))


@router.delete("/{project_id}/members/{member_id}")
async def remove_member(
    project_id: str,
    member_id: str,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await remove_project_member(db, project_id, user_id, member_id))
