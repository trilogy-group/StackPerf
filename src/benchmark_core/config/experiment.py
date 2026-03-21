"""Experiment configuration models."""

from pydantic import Field

from .base import BenchmarkConfigBase


class ExperimentConfig(BenchmarkConfigBase):
    """A named comparison grouping that contains one or more variants."""

    variants: list[str] = Field(
        default_factory=list,
        description="List of variant names to compare",
    )

    # Comparison settings
    comparison_dimensions: list[str] = Field(
        default_factory=lambda: ["provider", "model", "harness_profile"],
        description="Dimensions to compare across",
    )
