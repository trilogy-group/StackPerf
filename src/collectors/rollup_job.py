"""Rollup jobs for computing request, session, variant, and experiment summaries."""

from typing import Any

from benchmark_core.models import MetricRollup, Request


class RollupJob:
    """Deterministic rollup job for computing summary metrics."""

    async def compute_request_metrics(self, request: Request) -> list[MetricRollup]:
        """Compute metrics for a single request."""
        rollups: list[MetricRollup] = []
        # Placeholder: actual implementation
        return rollups

    async def compute_session_metrics(
        self,
        session_id: str,
        requests: list[Request],
    ) -> list[MetricRollup]:
        """Compute aggregate metrics for a session."""
        rollups: list[MetricRollup] = []
        # Placeholder: actual implementation
        return rollups

    async def compute_variant_metrics(
        self,
        variant_id: str,
        sessions: list[Any],
    ) -> list[MetricRollup]:
        """Compute aggregate metrics for a variant across sessions."""
        rollups: list[MetricRollup] = []
        # Placeholder: actual implementation
        return rollups

    async def compute_experiment_metrics(
        self,
        experiment_id: str,
        variants: list[Any],
    ) -> list[MetricRollup]:
        """Compute comparison metrics for an experiment."""
        rollups: list[MetricRollup] = []
        # Placeholder: actual implementation
        return rollups
