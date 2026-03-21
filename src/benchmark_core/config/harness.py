"""Harness profile configuration models."""

from enum import Enum

from pydantic import BaseModel, Field, field_validator

from .base import BenchmarkConfigBase
from .provider import ProtocolSurface


class RenderFormat(str, Enum):
    """Output format for rendered harness environment."""

    SHELL = "shell"  # Bash/sh environment variables export
    DOTENV = "dotenv"  # .env file format
    JSON = "json"  # JSON key-value pairs


class LaunchCheck(BaseModel):
    """A validation check before harness launch."""

    description: str = Field(..., description="What to check")
    command: str | None = Field(None, description="Shell command to verify")
    expected_pattern: str | None = Field(None, description="Expected output pattern")


class HarnessProfileConfig(BenchmarkConfigBase):
    """Harness profile describing how to connect a harness to the proxy."""

    protocol_surface: ProtocolSurface = Field(
        ...,
        description="Protocol surface this harness expects",
    )

    # Environment variable names
    base_url_env: str = Field(
        ...,
        description="Environment variable name for proxy base URL",
    )
    api_key_env: str = Field(
        ...,
        description="Environment variable name for API key",
    )
    model_env: str = Field(
        ...,
        description="Environment variable name for model name",
    )

    # Extra environment variables
    extra_env: dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variable templates",
    )

    # Rendering
    render_format: RenderFormat = Field(
        RenderFormat.SHELL,
        description="Default output format for rendering",
    )

    # Launch checks
    launch_checks: list[LaunchCheck] = Field(
        default_factory=list,
        description="Pre-launch validation checks",
    )

    @field_validator("extra_env")
    @classmethod
    def validate_extra_env_templates(cls, v: dict[str, str]) -> dict[str, str]:
        """Validate that extra_env templates are safe to render."""
        # Templates should not contain secrets directly
        for key, value in v.items():
            if len(value) > 64 and not any(c in value for c in ["{", "}", "{{", "}}"]):
                # Long literal values without templating are suspicious
                raise ValueError(
                    f"extra_env.{key} appears to contain a literal secret value. "
                    "Use templates like {{ model_alias }} instead."
                )
        return v
