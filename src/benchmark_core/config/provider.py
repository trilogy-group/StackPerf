"""Provider configuration models."""

from enum import Enum

from pydantic import BaseModel, Field

from .base import BenchmarkConfigBase


class ProtocolSurface(str, Enum):
    """Supported protocol surfaces for harness integration."""

    ANTHROPIC_MESSAGES = "anthropic_messages"
    OPENAI_RESPONSES = "openai_responses"
    OPENAI_CHAT = "openai_chat"


class ModelAlias(BaseModel):
    """Model alias configuration."""

    alias: str = Field(..., description="Local model alias exposed through proxy")
    upstream_model: str = Field(..., description="Upstream model identifier")


class RoutingDefaults(BaseModel):
    """Default routing parameters."""

    timeout_seconds: int | None = Field(None, description="Request timeout")
    extra_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Additional headers to send upstream",
    )
    extra_body: dict[str, str] = Field(
        default_factory=dict,
        description="Additional body fields",
    )


class ProviderConfig(BenchmarkConfigBase):
    """Provider configuration defining an upstream inference endpoint."""

    route_name: str = Field(..., description="LiteLLM route name")
    protocol_surface: ProtocolSurface = Field(
        ...,
        description="Primary protocol surface this provider exposes",
    )

    # Connection settings (as env var names, not values)
    upstream_base_url_env: str = Field(
        ...,
        description="Environment variable name for upstream base URL",
    )
    api_key_env: str = Field(
        ...,
        description="Environment variable name for API key",
    )

    # Model aliases
    models: list[ModelAlias] = Field(
        default_factory=list,
        description="Model aliases exposed through this provider",
    )

    # Routing
    routing_defaults: RoutingDefaults = Field(
        default_factory=RoutingDefaults,
        description="Default routing parameters",
    )

    def get_model_alias(self, alias: str) -> ModelAlias | None:
        """Find a model alias by name."""
        for model in self.models:
            if model.alias == alias:
                return model
        return None
