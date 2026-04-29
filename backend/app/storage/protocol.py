from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.result import Result
from app.core.errors import AppError


@runtime_checkable
class StorageBackend(Protocol):
    async def save(self, path: str, data: bytes) -> Result[str, AppError]:
        ...

    async def load(self, path: str) -> Result[bytes, AppError]:
        ...

    async def delete(self, path: str) -> Result[None, AppError]:
        ...

    async def exists(self, path: str) -> bool:
        ...

    def get_url(self, path: str) -> str:
        ...
