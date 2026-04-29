from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import PageParams


class CreateUserDto(BaseModel):
    model_config = ConfigDict(frozen=True)

    phone: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    nickname: str = Field(default="", max_length=64)
    captcha: str = Field(default="", max_length=6)


class UpdateUserDto(BaseModel):
    model_config = ConfigDict(frozen=True)

    nickname: str | None = Field(default=None, max_length=64)
    email: EmailStr | None = None


class UserLoginDto(BaseModel):
    model_config = ConfigDict(frozen=True)

    phone: str
    password: str


class AuthTokenPair(BaseModel):
    model_config = ConfigDict(frozen=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    phone: str = Field(..., min_length=1, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    nickname: str = Field(default="", max_length=64)
    captcha: str = Field(default="", max_length=6)


class LoginRequest(BaseModel):
    phone: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class SendSmsRequest(BaseModel):
    phone: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone: str
    nickname: str
    email: str | None = None
    avatar_url: str | None = None
    created_at: datetime


class UserProfileResponse(UserResponse):
    pass


class AuthResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
