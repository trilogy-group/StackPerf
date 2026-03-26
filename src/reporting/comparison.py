"""Comparison services for providers, models, harnesses, and configurations."""

from typing import Any

from benchmark_core.models import MetricRollup, Session


class ComparisonService:
    """Service for generating benchmark comparisons."""

    async def compare_sessions(
        self,
        session_ids: list[str],
    ) -> dict[str, Any]:
        """Compare metrics across multiple sessions."""
        # Placeholder: actual implementation
        return {}

    async def compare_variants(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Compare all variants within an experiment."""
        # Placeholder: actual implementation
        return {}

    async def compare_providers(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Compare metrics across providers for an experiment."""
        # Placeholder: actual implementation
        return {}

    async def compare_models(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Compare metrics across models for an experiment."""
        # Placeholder: actual implementation
        return {}

    async def compare_harnesses(
        self,
        experiment_id: str,
    ) -> dict[str, Any]:
        """Compare metrics across harnesses for an experiment."""
        # Placeholder: actual implementation
        return {}


class ReportBuilder:
    """Builder for structured benchmark reports."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def add_summary(self, summary: dict[str, Any]) -> "ReportBuilder":
        """Add summary section."""
        self._data["summary"] = summary
        return self

    def add_comparisons(self, comparisons: dict[str, Any]) -> "ReportBuilder":
        """Add comparisons section."""
        self._data["comparisons"] = comparisons
        return self

    def add_sessions(self, sessions: list[Session]) -> "ReportBuilder":
        """Add session details."""
        self._data["sessions"] = [s.model_dump() for s in sessions]
        return self

    def add_metrics(self, metrics: list[MetricRollup]) -> "ReportBuilder":
        """Add metric rollups."""
        self._data["metrics"] = [m.model_dump() for m in metrics]
        return self

    def build(self) -> dict[str, Any]:
        """Build the final report."""
        return self._data
