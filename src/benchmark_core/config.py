"""Configuration management using pydantic-settings."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/benchmark"
    database_echo: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10

    # LiteLLM
    litellm_base_url: str = "http://localhost:4000"
    litellm_admin_key: Optional[str] = None

    # Prometheus
    prometheus_url: str = "http://localhost:9090"

    # Collection settings
    collection_batch_size: int = 1000
    collection_window_seconds: int = 300


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
