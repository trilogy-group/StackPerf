"""Typed config schemas for providers, harness profiles, variants, experiments, task cards, and usage policies."""

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# Secret rejection patterns for config fields.
# Applied selectively to UsagePolicyProfile because its metadata fields
# (name, description, owner, team, customer, metadata tags) are user-configured
# and most likely to accidentally receive pasted secrets.
_SECRET_PATTERNS = [
    # OpenAI-style keys: sk- followed by 20+ alphanumeric chars (no hyphens in
    # body to avoid false positives on legitimate variant/model identifiers)
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    # Anthropic-style keys: sk-ant- followed by 20+ alphanumeric chars
    re.compile(r"sk-ant-[a-zA-Z0-9]{20,}"),
    # Bearer tokens: Bearer followed by 10+ alphanumeric chars
    re.compile(r"bearer\s+[a-zA-Z0-9]{10,}", re.IGNORECASE),
    # Generic API key with long alphanumeric tail
    re.compile(r"api[_-]?key[=:]\s*[a-zA-Z0-9]{10,}", re.IGNORECASE),
]


def _looks_like_secret(value: str) -> bool:
    """Check if a string value appears to contain a raw API key secret."""
    stripped = value.strip()
    return any(pattern.search(stripped) for pattern in _SECRET_PATTERNS)


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


class RedactionPolicy(BaseModel):
    """Redaction and retention policy reference for a usage profile."""

    model_config = {"extra": "forbid"}

    policy_name: str | None = Field(
        default=None,
        description="Reference to a named redaction/retention policy",
    )
    retain_prompts: bool | None = Field(
        default=None,
        description="Whether to retain prompt text (default: off)",
    )
    retain_responses: bool | None = Field(
        default=None,
        description="Whether to retain response text (default: off)",
    )
    retention_days: int | None = Field(
        default=None,
        description="Number of days to retain usage records before cleanup",
    )

    @field_validator("policy_name")
    @classmethod
    def validate_policy_name_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("policy_name must not be empty or whitespace")
        return v

    @field_validator("retention_days")
    @classmethod
    def validate_retention_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("retention_days must be positive")
        return v


class UsagePolicyProfile(BaseModel):
    """A named usage policy profile for sessionless proxy key creation.

    Defines defaults and constraints for a class of proxy keys
    (e.g., a team or customer tier).
    """

    model_config = {"extra": "forbid"}

    name: str = Field(..., description="Policy profile identifier")
    description: str = Field(default="", description="Human-readable description")
    allowed_models: list[str] = Field(
        default_factory=list,
        description="Model aliases permitted under this policy",
    )
    budget_duration: str | None = Field(
        default=None,
        description="Budget interval (e.g., 1d, 30d, 12h, 5m). Must match /^[1-9][0-9]*[dhm]$/.",
    )
    budget_amount: float | None = Field(
        default=None,
        description="Budget limit in currency units",
    )
    ttl_seconds: int | None = Field(
        default=None,
        description="Key TTL in seconds (time-to-live before expiration)",
    )
    owner: str | None = Field(
        default=None,
        description="Default owner label for keys created under this policy",
    )
    team: str | None = Field(
        default=None,
        description="Default team label for keys created under this policy",
    )
    customer: str | None = Field(
        default=None,
        description="Default customer label for keys created under this policy",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Default metadata tags for keys created under this policy",
    )
    redaction_policy: RedactionPolicy | None = Field(
        default=None,
        description="Redaction/retention policy reference",
    )

    @field_validator("name")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must not be empty or whitespace")
        return v

    @field_validator("allowed_models")
    @classmethod
    def validate_allowed_models(cls, v: list[str]) -> list[str]:
        for item in v:
            if not item or not item.strip():
                raise ValueError(
                    "allowed_models items must not be empty or whitespace"
                )
        seen = set()
        for item in v:
            if item in seen:
                raise ValueError(
                    f"allowed_models contains duplicate: {item!r}"
                )
            seen.add(item)
        return v

    @model_validator(mode="after")
    def reject_secret_values(self) -> "UsagePolicyProfile":
        """Reject fields that appear to contain raw API key secrets."""
        secret_fields: list[str] = []
        for field_name in ("name", "description", "owner", "team", "customer"):
            value = getattr(self, field_name)
            if value and _looks_like_secret(value):
                secret_fields.append(field_name)
        for key, value in self.metadata.items():
            if _looks_like_secret(value):
                secret_fields.append(f"metadata.{key}")
        if secret_fields:
            raise ValueError(
                f"usage policy fields contain secret-like values: {', '.join(secret_fields)}"
            )
        return self

    @field_validator("budget_amount")
    @classmethod
    def validate_budget_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("budget_amount must be positive")
        return v

    @field_validator("ttl_seconds")
    @classmethod
    def validate_ttl_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("ttl_seconds must be positive")
        return v

    @field_validator("budget_duration")
    @classmethod
    def validate_budget_duration_format(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^[1-9][0-9]*[dhm]$", v):
            raise ValueError(
                "budget_duration must match a duration format such as '1d', '30d', '12h', '5m'"
            )
        return v


class UsagePolicyConfig(BaseModel):
    """Top-level usage policy configuration file.

    Can contain one or more named usage policy profiles.
    Usage policy config is optional so current benchmark workflows
    do not require migration.
    """

    model_config = {"extra": "forbid"}

    profiles: list[UsagePolicyProfile] = Field(
        default_factory=list,
        description="Named usage policy profiles",
    )

    @field_validator("profiles")
    @classmethod
    def validate_unique_profile_names(cls, v: list[UsagePolicyProfile]) -> list[UsagePolicyProfile]:
        names = [p.name for p in v]
        if len(names) != len(set(names)):
            raise ValueError("duplicate usage policy profile names found")
        return v
