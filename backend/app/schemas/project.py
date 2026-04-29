from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str = ""
    is_public: bool = False
    cover_url: str | None = None
    member_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None


class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = Field(default="", max_length=5000)
    is_public: bool = False


class UpdateProjectRequest(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    description: str | None = Field(default=None, max_length=5000)
    is_public: bool | None = None


class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str
    role: str = "member"
    nickname: str = ""
    avatar_url: str | None = None


class AddMemberRequest(BaseModel):
    user_id: str
    role: str = Field(default="member", pattern="^(admin|member)$")


class ProjectDetailResponse(ProjectResponse):
    files: list["FileResponse"] = Field(default_factory=list)
    members: list[ProjectMemberResponse] = Field(default_factory=list)


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    project_id: str | None = None
    filename: str
    category: str
    mime_type: str = "application/octet-stream"
    file_size: int = 0
    duration_ms: int | None = None
    metadata: dict = Field(default_factory=dict, validation_alias="extra_meta")
    is_featured: bool = False
    created_at: datetime


class UpdateFileRequest(BaseModel):
    category: str | None = None
    is_featured: bool | None = None
    metadata: dict | None = None
