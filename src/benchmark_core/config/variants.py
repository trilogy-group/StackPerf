"""Variant configuration model."""

from typing import Annotated

from pydantic import Field, model_validator

from .base import BaseConfig, NameStr


class VariantConfig(BaseConfig, NameStr):
    """A benchmarkable combination of provider, model, harness, and settings."""

    provider: Annotated[str, Field(min_length=1)]
    provider_route: Annotated[str, Field(min_length=1)]
    model_alias: Annotated[str, Field(min_length=1)]
    harness_profile: Annotated[str, Field(min_length=1)]
    harness_env_overrides: dict[str, str] = Field(default_factory=dict)
    benchmark_tags: Annotated[dict[str, str], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_benchmark_tags(self) -> "VariantConfig":
        """Ensure required benchmark tags are present."""
        required_tags = {"provider", "model", "harness"}
        missing = required_tags - set(self.benchmark_tags.keys())
        if missing:
            raise ValueError(f"Missing required benchmark tags: {missing}")
        return self
