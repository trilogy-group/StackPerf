"""Typed config schemas for providers, harness profiles, variants, experiments, and task cards."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# Define valid protocol surfaces
ProtocolSurface = Literal["anthropic_messages", "openai_responses"]
RenderFormat = Literal["shell", "dotenv", "json", "toml"]


class ProviderModel(BaseModel):
    """Model alias definition within a provider config."""

    model_config = {"extra": "forbid"}

    alias: str = Field(..., description="Local alias for the model")
    upstream_model: str = Field(..., description="Upstream model identifier")


class RoutingDefaults(BaseModel):
    """Default routing configuration for provider."""

    model_config = {"extra": "forbid"}

    timeout_seconds: int | None = Field(default=None, description="Request timeout in seconds")
    extra_headers: dict[str, str] = Field(
        default_factory=dict, description="Additional headers to include"
    )


class ProviderConfig(BaseModel):
    """Upstream inference provider definition.

    Defines an upstream endpoint, route metadata, secret references,
    and model aliases exposed through LiteLLM.
    """

    model_config = {"extra": "forbid"}

    name: str = Field(..., description="Provider identifier")
    route_name: str | None = Field(default=None, description="Route name for LiteLLM proxy")
    protocol_surface: ProtocolSurface = Field(
        ..., description="Protocol surface (anthropic_messages or openai_responses)"
    )
    upstream_base_url_env: str = Field(
        ..., description="Environment variable name for upstream base URL"
    )
    api_key_env: str = Field(..., description="Environment variable name for API key")
    models: list[ProviderModel] = Field(
        default_factory=list, description="Model aliases exposed through LiteLLM"
    )
    routing_defaults: RoutingDefaults = Field(
        default_factory=RoutingDefaults, description="Default routing configuration"
    )

    @field_validator("name", "upstream_base_url_env", "api_key_env")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty or whitespace")
        return v

    @field_validator("models")
    @classmethod
    def validate_unique_aliases(cls, v: list[ProviderModel]) -> list[ProviderModel]:
        aliases = [m.alias for m in v]
        if len(aliases) != len(set(aliases)):
            raise ValueError("duplicate model aliases found")
        return v


class HarnessProfile(BaseModel):
    """How a harness is configured to talk to the proxy.

    Describes how to point a harness at the local LiteLLM proxy.
    """

    model_config = {"extra": "forbid"}

    name: str = Field(..., description="Profile identifier")
    protocol_surface: ProtocolSurface = Field(
        ..., description="Protocol surface (anthropic_messages or openai_responses)"
    )
    base_url_env: str = Field(..., description="Environment variable name for base URL")
    api_key_env: str = Field(..., description="Environment variable name for API key")
    model_env: str = Field(..., description="Environment variable name for model selection")
    extra_env: dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variable templates with {{ model_alias }} support",
    )
    render_format: RenderFormat = Field(
        default="shell", description="Output format for environment rendering"
    )
    launch_checks: list[str] = Field(
        default_factory=list,
        description="Verification checks before launching harness",
    )

    @field_validator("name", "base_url_env", "api_key_env", "model_env")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty or whitespace")
        return v


class Variant(BaseModel):
    """A benchmarkable combination of provider route, model, harness profile, and harness settings.

    Combines provider, model, harness profile, and harness-specific configuration values.
    """

    model_config = {"extra": "forbid"}

    name: str = Field(..., description="Variant identifier")
    provider: str = Field(..., description="Provider name reference")
    provider_route: str | None = Field(default=None, description="Provider route name")
    model_alias: str = Field(..., description="Model alias from provider config")
    harness_profile: str = Field(..., description="Harness profile name reference")
    harness_env_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Harness-specific environment variable overrides",
    )
    benchmark_tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags for benchmark categorization (must include harness, provider, model)",
    )

    @field_validator("name", "provider", "model_alias", "harness_profile")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty or whitespace")
        return v

    @model_validator(mode="after")
    def validate_benchmark_tags(self) -> "Variant":
        required_tags = {"harness", "provider", "model"}
        missing = required_tags - set(self.benchmark_tags.keys())
        if missing:
            raise ValueError(f"benchmark_tags must include: {', '.join(sorted(missing))}")
        return self


class Experiment(BaseModel):
    """A named comparison grouping that contains one or more variants.

    Groups comparable variants together for analysis.
    """

    model_config = {"extra": "forbid"}

    name: str = Field(..., description="Experiment identifier")
    description: str = Field(default="", description="Experiment description")
    variants: list[str] = Field(
        default_factory=list, description="List of variant names in this experiment"
    )

    @field_validator("name")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty or whitespace")
        return v

    @field_validator("variants")
    @classmethod
    def validate_unique_variants(cls, v: list[str]) -> list[str]:
        if len(v) != len(set(v)):
            raise ValueError("duplicate variant names found")
        return v


class TaskCard(BaseModel):
    """The benchmark task definition used for comparable sessions.

    Defines the interactive work and stop conditions.
    """

    model_config = {"extra": "forbid"}

    name: str = Field(..., description="Task card identifier")
    repo_path: str | None = Field(default=None, description="Path to repository for analysis")
    goal: str = Field(..., description="High-level task objective")
    starting_prompt: str = Field(..., description="Initial prompt for the harness")
    stop_condition: str = Field(..., description="Condition that signals task completion")
    session_timebox_minutes: int | None = Field(
        default=None, description="Maximum session duration in minutes"
    )
    notes: list[str] = Field(default_factory=list, description="Additional notes and constraints")

    @field_validator("name", "goal", "starting_prompt", "stop_condition")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty or whitespace")
        return v

    @field_validator("session_timebox_minutes")
    @classmethod
    def validate_timebox(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("session_timebox_minutes must be positive")
        return v
