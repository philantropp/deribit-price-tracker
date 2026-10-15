"""Application settings loaded from environment variables (and `.env`)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(
        description="SQLAlchemy async URL, e.g. postgresql+asyncpg://user:pass@host:5432/db",
    )
    celery_broker_url: str = "redis://localhost:6379/0"

    deribit_base_url: str = "https://www.deribit.com/api/v2"
    deribit_timeout_seconds: float = Field(default=10.0, gt=0)

    price_collection_interval_seconds: float = Field(default=60.0, gt=0)

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Read settings once per process; the cache keeps a single instance."""
    return Settings()
