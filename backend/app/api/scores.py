from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db_session
from app.core.result import Ok, Err
from app.core.respond import respond
from app.services.score_service import get_score, get_score_by_file

router = APIRouter(prefix="/scores", tags=["scores"], redirect_slashes=False)


@router.get("/{score_id}")
async def get_one(score_id: str, db: AsyncSession = Depends(get_db_session)):
    return respond(await get_score(db, score_id))


@router.get("/{score_id}/render")
async def render(
    score_id: str,
    page: int = Query(default=1, ge=1),
    width: int = Query(default=900),
    db: AsyncSession = Depends(get_db_session),
):
    result = await get_score(db, score_id)
    match result:
        case Ok(value):
            return {"ok": True, "data": {"score": value.model_dump(mode="json"), "render": value.vexflow_json or {}}}
        case Err():
            return respond(result)


@router.get("/{score_id}/export")
async def export_score(
    score_id: str,
    format: str = Query("musicxml"),
    db: AsyncSession = Depends(get_db_session),
):
    # NOTE(gap): MIDI and PDF export are stubs — return placeholder JSON.
    # MusicXML export works only if ScoreRecord.musicxml is populated (requires algorithm).
    result = await get_score(db, score_id)
    match result:
        case Ok(value):
            if format == "musicxml" and value.musicxml:
                return PlainTextResponse(content=value.musicxml, media_type="application/xml")
            return {"ok": True, "data": {"format": format}}
        case Err():
            return respond(result)


@router.get("/by-file/{file_id}")
async def get_by_file(file_id: str, db: AsyncSession = Depends(get_db_session)):
    return respond(await get_score_by_file(db, file_id))
