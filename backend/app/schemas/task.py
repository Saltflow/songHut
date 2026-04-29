from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TaskParamsSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    instrument: int = Field(default=1, ge=0, le=127)
    is_drum: bool = False
    is_bass: bool = False
    is_chord: bool = False
    chord_style: str = Field(default="block", pattern="^(block|arpeggio|both)$")
    key_signature: str | None = None
    tempo: int | None = None


class CreateMelodyTaskRequest(BaseModel):
    project_id: str
    source_file_id: str
    params: TaskParamsSchema = Field(default_factory=TaskParamsSchema)


class CreateAccompanimentTaskRequest(BaseModel):
    project_id: str
    source_file_id: str
    params: TaskParamsSchema = Field(default_factory=TaskParamsSchema)


class CreateScoreTaskRequest(BaseModel):
    source_file_id: str


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    project_id: str | None = None
    source_file_id: str
    result_file_id: str | None = None
    task_type: str
    params: dict = Field(default_factory=dict)
    status: str = "pending"
    progress: float = 0.0
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
