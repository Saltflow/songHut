from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "SongHut 2.0"
    debug: bool = False
    secret_key: str = "change-me-in-production"
    allowed_origins: list[str] = ["*"]

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/songhut"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    redis_url: str = "redis://localhost:6379/0"

    storage_backend: str = "local"
    storage_local_path: str = "./data"
    max_file_size_mb: int = 200

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 30

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    algorithm_temp_dir: str = "./tmp/algorithm"
    soundfont_path: str = "./assets/soundfont.sf2"
    crepe_model_size: str = "tiny"


@lru_cache
def get_settings() -> Settings:
    return Settings()
