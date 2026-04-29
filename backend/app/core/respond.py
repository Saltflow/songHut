from __future__ import annotations

from fastapi.responses import JSONResponse

from app.core.result import Ok, Err


def respond(result):
    match result:
        case Ok(value):
            if value is None:
                return {"ok": True, "data": None}
            if hasattr(value, "model_dump"):
                return {"ok": True, "data": value.model_dump(mode="json")}
            return {"ok": True, "data": value}
        case Err(error):
            return JSONResponse(
                status_code=error.http_status,
                content=error.to_dict(),
            )
