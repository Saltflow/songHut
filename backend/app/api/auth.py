from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db_session
from app.core.respond import respond
from app.core.result import Ok, Err
from app.core.logging import logger
from app.schemas.auth import (
    RegisterRequest, LoginRequest, RefreshRequest, SendSmsRequest,
    CreateUserDto, UserLoginDto,
)
from app.services.auth_service import (
    register_user, login_user, refresh_auth_tokens,
)

router = APIRouter(prefix="/auth", tags=["auth"], redirect_slashes=False)


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db_session)):
    logger.info("auth.register.attempt", phone=body.phone)
    dto = CreateUserDto(
        phone=body.phone, password=body.password,
        nickname=body.nickname, captcha=body.captcha,
    )
    result = respond(await register_user(db, dto))
    if isinstance(result, dict) and result.get("ok") is False:
        logger.warning("auth.register.failed", phone=body.phone)
    return result


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    logger.info("auth.login.attempt", phone=body.phone)
    dto = UserLoginDto(phone=body.phone, password=body.password)
    result = respond(await login_user(db, dto))
    if isinstance(result, dict) and result.get("ok") is False:
        logger.warning("auth.login.failed", phone=body.phone)
    return result


@router.post("/refresh")
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db_session)):
    logger.info("auth.refresh.attempt")
    return respond(await refresh_auth_tokens(db, body.refresh_token))


@router.post("/logout")
async def logout():
    # TODO(verify): needs real PG + uvicorn — stub, does not invalidate token
    logger.info("auth.logout")
    return {"ok": True, "data": None}


@router.post("/send-sms")
async def send_sms(body: SendSmsRequest):
    # TODO(verify): needs real PG + uvicorn — stub, no SMS API integrated
    logger.info("auth.send-sms.stub", phone=body.phone)
    return {"ok": True, "data": {"expires_in": 300}}
