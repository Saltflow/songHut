from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user_id, get_db_session
from app.core.respond import respond
from app.services.auth_service import get_user_by_id, update_user

router = APIRouter(prefix="/users", tags=["users"], redirect_slashes=False)


@router.get("/me")
async def get_me(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await get_user_by_id(db, user_id))


@router.patch("/me")
async def update_me(
    body: dict,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
):
    nickname = body.get("nickname")
    email = body.get("email")
    return respond(await update_user(db, user_id, nickname, email))


@router.post("/me/avatar")
async def upload_avatar(
    user_id: str = Depends(get_current_user_id),
):
    # TODO(verify): needs real PG + uvicorn — stub, does not save file
    return {"ok": True, "data": {"avatar_url": None}}


@router.get("/{target_user_id}")
async def get_user(
    target_user_id: str,
    db: AsyncSession = Depends(get_db_session),
):
    return respond(await get_user_by_id(db, target_user_id))
