from __future__ import annotations

from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_access_token
from app.core.result import Ok, Err


async def get_current_user_id(
    authorization: str = Header(...),
) -> str:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    result = verify_access_token(token)
    match result:
        case Ok(value):
            return str(value)
        case Err(error):
            raise HTTPException(status_code=error.http_status, detail=error.to_dict()["error"]["message"])


async def get_db_session() -> AsyncSession:
    async for session in get_db():
        yield session


async def get_optional_user_id(
    authorization: str | None = Header(None),
) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    result = verify_access_token(token)
    match result:
        case Ok(value):
            return str(value)
        case Err():
            return None
