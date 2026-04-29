from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.user import new_uuid, utcnow


class ScoreRecord(Base):
    __tablename__ = "scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("files.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    source_task_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    musicxml: Mapped[str | None] = mapped_column(Text, nullable=True)
    vexflow_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    key_signature: Mapped[str] = mapped_column(String(16), default="C")
    time_signature: Mapped[str] = mapped_column(String(16), default="4/4")
    tempo: Mapped[int] = mapped_column(Integer, default=120)
    measures_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
