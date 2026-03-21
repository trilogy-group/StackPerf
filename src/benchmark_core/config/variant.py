"""Variant configuration models."""

from pydantic import BaseModel, Field

from .base import BenchmarkConfigBase


class VariantConfig(BenchmarkConfigBase):
    """A benchmarkable combination of provider, model, harness profile, and settings."""

    # Provider and model
    provider: str = Field(..., description="Provider config name")
    provider_route: str = Field(..., description="Provider route name")
    model_alias: str = Field(..., description="Model alias to use")

    # Harness
    harness_profile: str = Field(
        ..., description="Harness profile config name"
    )
    harness_env_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variable overrides for this variant",
    )

    # Benchmark tags for correlation
    benchmark_tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags for request correlation",
    )

    def get_config_fingerprint(self) -> str:
        """Generate a deterministic fingerprint of variant configuration."""
        import hashlib
        import json

        data = {
            "provider": self.provider,
            "provider_route": self.provider_route,
            "model_alias": self.model_alias,
            "harness_profile": self.harness_profile,
            "harness_env_overrides": dict(sorted(self.harness_env_overrides.items())),
        }
        content = json.dumps(data, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
