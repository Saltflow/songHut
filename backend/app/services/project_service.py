from __future__ import annotations

import math

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectMember
from app.models.file_record import FileRecord
from app.core.result import Result, Ok, Err
from app.core.errors import AppError, not_found, forbidden
from app.schemas.project import (
    ProjectResponse,
    ProjectDetailResponse,
    ProjectMemberResponse,
    FileResponse,
    CreateProjectRequest,
    UpdateProjectRequest,
)
from app.schemas.common import PageParams, PageResponse


async def list_projects(
    db: AsyncSession, user_id: str, page: PageParams,
) -> Result[PageResponse[ProjectResponse], AppError]:

    subq = (
        select(ProjectMember.project_id)
        .where(ProjectMember.user_id == user_id)
        .subquery()
    )

    count_q = select(func.count(Project.id)).where(
        (Project.id.in_(select(subq.c.project_id))))
    total = (await db.execute(count_q)).scalar_one()

    offset = (page.page - 1) * page.page_size
    q = (
        select(Project)
        .where(Project.id.in_(select(subq.c.project_id)))
        .order_by(Project.created_at.desc())
        .offset(offset)
        .limit(page.page_size)
    )
    projects = (await db.execute(q)).scalars().all()

    # count members
    items = []
    for p in projects:
        member_count = (await db.execute(
            select(func.count(ProjectMember.user_id)).where(
                ProjectMember.project_id == p.id)
        )).scalar_one()

        items.append(ProjectResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            is_public=p.is_public,
            cover_url=p.cover_file_id,
            member_count=member_count,
            created_at=p.created_at,
            updated_at=p.updated_at,
        ))

    return Ok(PageResponse(
        items=items,
        total=total,
        page=page.page,
        page_size=page.page_size,
        total_pages=math.ceil(total / page.page_size) if total > 0 else 1,
    ))

async def create_project(
    db: AsyncSession, user_id: str, dto: CreateProjectRequest,
) -> Result[ProjectResponse, AppError]:

    project = Project(
        name=dto.name,
        description=dto.description,
        is_public=dto.is_public,
    )
    db.add(project)
    await db.flush()

    member = ProjectMember(project_id=project.id, user_id=user_id, role="owner")
    db.add(member)
    await db.commit()
    await db.refresh(project)

    return Ok(ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        is_public=project.is_public,
        cover_url=project.cover_file_id,
        member_count=1,
        created_at=project.created_at,
        updated_at=project.updated_at,
    ))


async def get_project_detail(
    db: AsyncSession, project_id: str, user_id: str,
) -> Result[ProjectDetailResponse, AppError]:

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
            return Err(forbidden("You do not have access to this project"))

    # get members with nicknames
    from app.models.user import User
    member_rows = (await db.execute(
        select(ProjectMember, User.nickname).join(
            User, User.id == ProjectMember.user_id, isouter=True
        ).where(ProjectMember.project_id == project_id)
    )).all()

    members = []
    for pm, nickname in member_rows:
        members.append(ProjectMemberResponse(
            user_id=pm.user_id,
            role=pm.role,
            nickname=nickname or "",
        ))

    # get files
    file_rows = (await db.execute(
        select(FileRecord).where(FileRecord.project_id == project_id)
        .order_by(FileRecord.created_at.desc())
    )).scalars().all()

    files = [FileResponse.model_validate(f) for f in file_rows]

    return Ok(ProjectDetailResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        is_public=project.is_public,
        cover_url=project.cover_file_id,
        member_count=len(members),
        created_at=project.created_at,
        updated_at=project.updated_at,
        members=members,
        files=files,
    ))


async def update_project(
    db: AsyncSession, project_id: str, user_id: str, dto: UpdateProjectRequest,
) -> Result[ProjectResponse, AppError]:

    project = await db.get(Project, project_id)
    if not project:
        return Err(not_found("project", project_id))

    # check ownership
    member_row = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = member_row.scalar_one_or_none()
    if not member or member.role not in ("owner", "admin"):
        return Err(forbidden("Only owner or admin can update the project"))

    if dto.name is not None:
        project.name = dto.name
    if dto.description is not None:
        project.description = dto.description
    if dto.is_public is not None:
        project.is_public = dto.is_public

    await db.commit()
    await db.refresh(project)

    return Ok(ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        is_public=project.is_public,
        cover_url=project.cover_file_id,
        member_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at,
    ))


async def delete_project(
    db: AsyncSession, project_id: str, user_id: str,
) -> Result[None, AppError]:

    project = await db.get(Project, project_id)
    if not project:
        return Err(not_found("project", project_id))

    member_row = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = member_row.scalar_one_or_none()
    if not member or member.role != "owner":
        return Err(forbidden("Only the owner can delete this project"))

    await db.delete(project)
    await db.commit()
    return Ok(None)


async def add_project_member(
    db: AsyncSession, project_id: str, operator_id: str, new_user_id: str, role: str,
) -> Result[ProjectMemberResponse, AppError]:

    # check operator is owner/admin
    op_row = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == operator_id,
        )
    )
    op = op_row.scalar_one_or_none()
    if not op or op.role not in ("owner", "admin"):
        return Err(forbidden())

    # check if already a member
    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == new_user_id,
        )
    )
    if existing.scalar_one_or_none():
        return Err(AppError(code="CONFLICT", message="User is already a member", http_status=409))

    member = ProjectMember(project_id=project_id, user_id=new_user_id, role=role)
    db.add(member)
    await db.commit()

    return Ok(ProjectMemberResponse(user_id=new_user_id, role=role))


async def remove_project_member(
    db: AsyncSession, project_id: str, operator_id: str, member_id: str,
) -> Result[None, AppError]:

    op_row = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == operator_id,
        )
    )
    op = op_row.scalar_one_or_none()
    if not op or op.role not in ("owner", "admin"):
        return Err(forbidden())

    target = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == member_id,
        )
    )
    target_member = target.scalar_one_or_none()
    if not target_member:
        return Err(not_found("member", member_id))

    if target_member.role == "owner":
        return Err(forbidden("Cannot remove the project owner"))

    await db.delete(target_member)
    await db.commit()
    return Ok(None)
