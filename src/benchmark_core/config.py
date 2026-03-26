"""Typed config schemas for providers, harness profiles, variants, experiments, and task cards."""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class ProviderConfig(BaseModel):
    """Upstream inference provider definition."""

    model_config = {"extra": "forbid"}

    name: str = Field(..., description="Provider identifier")
    base_url: str | None = Field(None, description="Provider API base URL")
    api_key_env: str = Field(..., description="Environment variable name for API key")

    @field_validator("name", "api_key_env")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be empty or whitespace")
        return v


class HarnessProfile(BaseModel):
    """How a harness is configured to talk to the proxy."""

    name: str = Field(..., description="Profile identifier")
    protocol: str = Field(..., description="Proxy protocol surface (openai, anthropic, etc.)")
    env_template: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variable template for harness",
    )


class Variant(BaseModel):
    """A benchmarkable combination of provider route, model, harness profile, and harness settings."""

    name: str = Field(..., description="Variant identifier")
    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model identifier or alias")
    harness_profile: str = Field(..., description="Harness profile name")
    harness_settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Harness-specific configuration",
    )


class Experiment(BaseModel):
    """A named comparison grouping that contains one or more variants."""

    name: str = Field(..., description="Experiment identifier")
    description: str = Field(default="", description="Experiment description")
    variant_ids: list[str] = Field(default_factory=list, description="List of variant IDs")


class TaskCard(BaseModel):
    """The benchmark task definition used for comparable sessions."""

    id: str = Field(..., description="Task card identifier")
    description: str = Field(default="", description="Task description")
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Criteria for task completion",
    )
