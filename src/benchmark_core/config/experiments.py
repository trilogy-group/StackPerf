"""Experiment configuration model."""

from typing import Annotated, Any

from pydantic import Field, field_validator

from .base import BaseConfig, NameStr


class ExperimentConfig(BaseConfig, NameStr):
    """An experiment grouping comparable variants."""

    description: str | None = None
    variants: Annotated[list[str], Field(min_length=1)]
    comparison_dimensions: list[str] = Field(
        default_factory=lambda: ["provider", "model", "harness_profile"],
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("variants")
    @classmethod
    def validate_unique_variants(cls, v: list[str]) -> list[str]:
        """Ensure variants are unique within an experiment."""
        if len(v) != len(set(v)):
            raise ValueError("Variants must be unique within an experiment")
        return v
