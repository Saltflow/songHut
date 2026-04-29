from __future__ import annotations

from pathlib import Path

import aiofiles

from app.core.result import Result, Ok, Err
from app.core.errors import AppError
from app.storage.protocol import StorageBackend


class LocalStorage(StorageBackend):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, path: str, data: bytes) -> Result[str, AppError]:
        full_path = self.base_path / path
        try:
            full_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(full_path, "wb") as f:
                await f.write(data)
            return Ok(str(full_path))
        except OSError as e:
            return Err(AppError(
                code="STORAGE_FAILED",
                message=f"Failed to save file: {e}",
                http_status=500,
            ))

    async def load(self, path: str) -> Result[bytes, AppError]:
        full_path = self.base_path / path
        if not full_path.exists():
            return Err(AppError(
                code="FILE_NOT_FOUND",
                message=f"File not found: {path}",
                http_status=404,
            ))
        try:
            async with aiofiles.open(full_path, "rb") as f:
                data = await f.read()
            return Ok(data)
        except OSError as e:
            return Err(AppError(
                code="STORAGE_FAILED",
                message=f"Failed to read file: {e}",
                http_status=500,
            ))

    async def delete(self, path: str) -> Result[None, AppError]:
        full_path = self.base_path / path
        try:
            if full_path.exists():
                full_path.unlink()
            return Ok(None)
        except OSError as e:
            return Err(AppError(
                code="STORAGE_FAILED",
                message=f"Failed to delete file: {e}",
                http_status=500,
            ))

    async def exists(self, path: str) -> bool:
        return (self.base_path / path).exists()

    def get_url(self, path: str) -> str:
        return f"/files/{path}"
