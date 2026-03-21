"""Base configuration models."""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, cast

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings

from uuid6 import uuid7


class BaseConfig(BaseModel):
    """Base configuration model with strict validation."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class NameStr(BaseModel):
    """Mixin for named configuration items."""

    name: Annotated[str, Field(min_length=1, max_length=255, pattern=r"^[a-z0-9][a-z0-9-]*$")]


class BenchmarkConfigBase(BaseModel):
    """Base class for benchmark configuration objects."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    name: str = Field(..., description="Unique configuration name")
    description: str | None = Field(None, description="Human-readable description")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Settings(BaseSettings):
    """Runtime settings from environment."""

    # Database
    database_url: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/stackperf",
        description="PostgreSQL connection URL",
    )

    # LiteLLM proxy
    litellm_base_url: str = Field(
        "http://localhost:4000",
        description="LiteLLM proxy base URL",
    )
    litellm_master_key: str | None = Field(
        None,
        description="LiteLLM master key for admin operations",
    )

    # Config paths
    config_root: Path = Field(
        Path("configs"),
        description="Root directory for configuration files",
    )

    # Session defaults
    session_credential_ttl_hours: int = Field(
        24,
        description="Default TTL for session credentials",
    )

    # Content capture
    capture_content: bool = Field(
        False,
        description="Whether to capture prompt/response content",
    )

    model_config = {
        "env_prefix": "STACKPERF_",
        "env_file": ".env",
        "extra": "ignore",
    }


def load_yaml_config(path: Path) -> dict[str, Any]:
    """Load and parse a YAML configuration file."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r") as f:
        data = yaml.safe_load(f)

    if data is None:
        return {}

    return cast(dict[str, Any], data)
