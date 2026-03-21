"""Experiment configuration model."""

from typing import Annotated

from pydantic import Field, field_validator

from .base import BaseConfig, NameStr


class ExperimentConfig(BaseConfig, NameStr):
    """An experiment grouping comparable variants."""

    variants: Annotated[list[str], Field(min_length=1)]
    description: str | None = None

    @field_validator("variants")
    @classmethod
    def validate_unique_variants(cls, v: list[str]) -> list[str]:
        """Ensure variants are unique within an experiment."""
        if len(v) != len(set(v)):
            raise ValueError("Variants must be unique within an experiment")
        return v
