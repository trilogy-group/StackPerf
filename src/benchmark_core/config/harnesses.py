"""Harness profile configuration model."""

from enum import StrEnum
from typing import Annotated, Any

from pydantic import Field

from .base import BaseConfig, NameStr
from .providers import ProtocolSurface


class RenderFormat(StrEnum):
    """Supported render formats for harness environment snippets."""

    SHELL = "shell"
    DOTENV = "dotenv"
    JSON = "json"


class LaunchCheck(BaseConfig):
    """A launch check item for documentation."""

    description: str
    command: str | None = None
    expected_pattern: str | None = None


class HarnessProfileConfig(BaseConfig, NameStr):
    """Harness profile describing how to point a harness at the local proxy."""

    description: str | None = None
    protocol_surface: ProtocolSurface
    base_url_env: Annotated[str, Field(min_length=1)]
    api_key_env: Annotated[str, Field(min_length=1)]
    model_env: Annotated[str, Field(min_length=1)]
    extra_env: dict[str, str] = Field(default_factory=dict)
    render_format: RenderFormat = RenderFormat.SHELL
    launch_checks: list[LaunchCheck] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
