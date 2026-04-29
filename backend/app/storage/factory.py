from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.storage.protocol import StorageBackend
from app.storage.local import LocalStorage


@lru_cache
def get_storage() -> StorageBackend:
    settings = get_settings()
    # NOTE(gap): only "local" backend implemented. "s3" falls through to LocalStorage.
    # S3Storage (MinIO/AWS S3) planned for Phase 5.
    match settings.storage_backend:
        case "s3":
            # TODO(verify): needs S3Storage implementation at app/storage/s3.py
            return LocalStorage(settings.storage_local_path)
        case _:
            return LocalStorage(settings.storage_local_path)
