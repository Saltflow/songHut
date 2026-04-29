from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.core.security import verify_access_token
from app.core.result import Ok, Err
from app.models.task_record import TaskRecord
from sqlalchemy import select

router = APIRouter(prefix="/ws", tags=["ws"])


class TaskWebSocketManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        self.connections.setdefault(task_id, []).append(websocket)

    def disconnect(self, task_id: str, websocket: WebSocket):
        conns = self.connections.get(task_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns and task_id in self.connections:
            del self.connections[task_id]

    async def broadcast(self, task_id: str, event: dict):
        conns = self.connections.get(task_id, [])
        dead = []
        for ws in conns:
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(task_id, ws)


manager = TaskWebSocketManager()


@router.websocket("/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str):
    await websocket.accept()

    authenticated = False
    user_id = None

    try:
        # wait for auth message
        while not authenticated:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "auth":
                token = msg.get("token", "")
                if token.startswith("Bearer "):
                    token = token[7:]
                result = verify_access_token(token)
                match result:
                    case Ok(uid):
                        user_id = str(uid)
                        authenticated = True
                    case Err(_):
                        await websocket.send_json({
                            "event": "auth:failed",
                            "data": {"message": "Invalid token"},
                        })
                        return

            elif msg.get("event") == "pong":
                pass  # heartbeat
            else:
                await websocket.send_json({"event": "error", "data": {"message": "Auth required first"}})

        manager.connections.setdefault(task_id, []).append(websocket)

        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            if msg.get("event") == "pong":
                pass
            # we don't handle other client messages currently

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect(task_id, websocket)
