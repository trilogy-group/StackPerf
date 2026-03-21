"""Provider configuration model."""

from enum import StrEnum
from typing import Annotated, Any

from pydantic import Field, field_validator

from .base import BaseConfig, NameStr


class ProtocolSurface(StrEnum):
    """Supported protocol surfaces for harness connections."""

    ANTHROPIC_MESSAGES = "anthropic_messages"
    OPENAI_CHAT = "openai_chat"
    OPENAI_RESPONSES = "openai_responses"


class ModelAlias(BaseConfig):
    """Model alias mapping."""

    alias: Annotated[str, Field(min_length=1, max_length=255)]
    upstream_model: Annotated[str, Field(min_length=1, max_length=255)]


class RoutingDefaults(BaseConfig):
    """Default routing parameters."""

    timeout_seconds: int = 180
    max_retries: int = 3
    extra_headers: dict[str, str] = Field(default_factory=dict)


class ProviderConfig(BaseConfig, NameStr):
    """Provider configuration defining an upstream inference endpoint."""

    description: str | None = None
    route_name: Annotated[str, Field(min_length=1, max_length=255)]
    protocol_surface: ProtocolSurface
    upstream_base_url_env: Annotated[str, Field(min_length=1)]
    api_key_env: Annotated[str, Field(min_length=1)]
    models: list[ModelAlias] = Field(min_length=1)
    routing_defaults: RoutingDefaults = Field(default_factory=RoutingDefaults)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("models")
    @classmethod
    def validate_unique_aliases(cls, v: list[ModelAlias]) -> list[ModelAlias]:
        """Ensure model aliases are unique within a provider."""
        aliases = [m.alias for m in v]
        if len(aliases) != len(set(aliases)):
            raise ValueError("Model aliases must be unique within a provider")
        return v
