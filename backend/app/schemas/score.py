from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_id: str
    source_task_id: str | None = None
    musicxml: str | None = None
    vexflow_json: dict | None = None
    key_signature: str = "C"
    time_signature: str = "4/4"
    tempo: int = 120
    measures_count: int = 0
    created_at: datetime
