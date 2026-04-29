"""Auth and user management services.
NOTE(gap): user_service was designed as a separate module in 03-后端模块设计.md.
Current implementation merges user functions here to reduce file count.
Extract to app/services/user_service.py if this file grows beyond ~200 lines."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.core.result import Result, Ok, Err
from app.core.errors import (
    AppError,
    invalid_credentials,
    phone_exists,
    token_invalid,
    not_found,
)
from app.schemas.auth import (
    CreateUserDto,
    UserLoginDto,
    AuthTokenPair,
    UserResponse,
    AuthResponse,
)


async def register_user(db: AsyncSession, dto: CreateUserDto) -> Result[AuthResponse, AppError]:
    existing = await db.execute(select(User).where(User.phone == dto.phone))
    if existing.scalar_one_or_none():
        return Err(phone_exists())

    user = User(
        phone=dto.phone,
        password_hash=hash_password(dto.password),
        nickname=dto.nickname or "",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(UUID(user.id))
    refresh_token = create_refresh_token(UUID(user.id))

    return Ok(AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
    ))


async def login_user(db: AsyncSession, dto: UserLoginDto) -> Result[AuthResponse, AppError]:
    result = await db.execute(select(User).where(User.phone == dto.phone))
    user = result.scalar_one_or_none()

    if not user or not verify_password(dto.password, user.password_hash):
        return Err(invalid_credentials())

    access_token = create_access_token(UUID(user.id))
    refresh_token = create_refresh_token(UUID(user.id))

    return Ok(AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        refresh_token=refresh_token,
    ))


async def refresh_auth_tokens(
    db: AsyncSession, token: str
) -> Result[AuthTokenPair, AppError]:

    result = verify_refresh_token(token)
    match result:
        case Ok(user_id):
            pass
        case Err(error):
            return Err(error)

    user = await db.get(User, str(user_id))
    if not user:
        return Err(token_invalid())

    access_token = create_access_token(UUID(user.id))
    refresh_token = create_refresh_token(UUID(user.id))

    return Ok(AuthTokenPair(access_token=access_token, refresh_token=refresh_token))


async def get_user_by_id(db: AsyncSession, user_id: str) -> Result[UserResponse, AppError]:
    user = await db.get(User, user_id)
    if not user:
        return Err(not_found("user", user_id))
    return Ok(UserResponse.model_validate(user))


async def update_user(
    db: AsyncSession, user_id: str, nickname: str | None, email: str | None
) -> Result[UserResponse, AppError]:

    user = await db.get(User, user_id)
    if not user:
        return Err(not_found("user", user_id))

    if nickname is not None:
        user.nickname = nickname
    if email is not None:
        user.email = email

    await db.commit()
    await db.refresh(user)
    return Ok(UserResponse.model_validate(user))
