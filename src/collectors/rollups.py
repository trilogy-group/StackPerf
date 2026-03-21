"""Metric rollup computation for sessions, variants, and experiments."""
import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.db.models import MetricRollupModel, RequestModel, SessionModel
from benchmark_core.models import MetricRollup, RequestStatus, RollupScopeType
from benchmark_core.repositories.metric_rollup_repository import MetricRollupRepository


logger = structlog.get_logger()


class EmptyWindowError(Exception):
    """Raised when a rollup window has no data."""
    pass


class MetricRollupService:
    """Service for computing metric rollups."""

    # Metric names that must be computed
    SESSION_METRICS = [
        "request_count",
        "success_count",
        "error_count",
        "median_latency_ms",
        "p95_latency_ms",
        "median_ttft_ms",
        "total_input_tokens",
        "total_output_tokens",
        "median_output_tokens_per_second",
        "cache_hit_ratio",
    ]

    VARIANT_METRICS = [
        "session_count",
        "session_success_rate",
        "median_session_duration_minutes",
        "median_latency_ms",
        "p95_latency_ms",
        "median_ttft_ms",
    ]

    EXPERIMENT_METRICS = [
        "variant_count",
        "total_session_count",
        "total_request_count",
        "median_latency_ms",
        "p95_latency_ms",
    ]

    def __init__(self, session: AsyncSession):
        self.session = session
        self.rollup_repo = MetricRollupRepository()

    def _percentile(self, values: List[float], percentile: float) -> Optional[float]:
        """Compute percentile safely.

        Args:
            values: List of values
            percentile: Percentile to compute (e.g., 95 for p95)

        Returns:
            Percentile value or None if empty
        """
        if not values:
            return None
        return float(np.percentile(values, percentile))

    def _median(self, values: List[float]) -> Optional[float]:
        """Compute median safely.

        Args:
            values: List of values

        Returns:
            Median value or None if empty
        """
        return self._percentile(values, 50)

    def _handle_empty_window(self, scope_type: RollupScopeType, scope_id: str) -> None:
        """Handle empty rollup window safely.

        Empty windows are logged but don't corrupt aggregates.
        """
        logger.info(
            "Empty rollup window",
            scope_type=scope_type.value,
            scope_id=scope_id,
        )

    async def compute_session_rollups(self, session_id: UUID) -> List[MetricRollup]:
        """Compute all rollup metrics for a session.

        Args:
            session_id: Session to compute rollups for

        Returns:
            List of computed MetricRollup models
        """
        # Fetch all requests for this session
        result = await self.session.execute(
            select(RequestModel).where(RequestModel.session_id == str(session_id))
        )
        requests = list(result.scalars().all())

        if not requests:
            self._handle_empty_window(RollupScopeType.SESSION, str(session_id))
            return []

        # Extract values for computation
        latencies = [r.latency_ms for r in requests if r.latency_ms is not None]
        ttfts = [r.ttft_ms for r in requests if r.ttft_ms is not None]
        output_tokens = [r.output_tokens for r in requests if r.output_tokens is not None]
        input_tokens = [r.input_tokens for r in requests if r.input_tokens is not None]
        cached_tokens = [r.cached_input_tokens for r in requests if r.cached_input_tokens is not None]
        
        # Compute token-per-second for each request
        tokens_per_second = []
        for r in requests:
            if r.output_tokens and r.latency_ms and r.latency_ms > 0:
                tps = (r.output_tokens / r.latency_ms) * 1000
                tokens_per_second.append(tps)

        # Count successes/errors
        success_count = sum(1 for r in requests if r.status == RequestStatus.SUCCESS)
        error_count = sum(1 for r in requests if r.status == RequestStatus.ERROR)

        # Cache hit ratio (requests with cached tokens / total requests with input)
        cache_hits = sum(1 for r in requests if r.cached_input_tokens and r.cached_input_tokens > 0)
        total_with_input = sum(1 for r in requests if r.input_tokens and r.input_tokens > 0)
        cache_hit_ratio = cache_hits / total_with_input if total_with_input > 0 else 0.0

        # Build metrics
        metrics = {
            "request_count": float(len(requests)),
            "success_count": float(success_count),
            "error_count": float(error_count),
            "total_input_tokens": float(sum(input_tokens)) if input_tokens else 0.0,
            "total_output_tokens": float(sum(output_tokens)) if output_tokens else 0.0,
            "cache_hit_ratio": cache_hit_ratio,
        }

        if latencies:
            metrics["median_latency_ms"] = self._median(latencies)
            metrics["p95_latency_ms"] = self._percentile(latencies, 95)
        
        if ttfts:
            metrics["median_ttft_ms"] = self._median(ttfts)
        
        if tokens_per_second:
            metrics["median_output_tokens_per_second"] = self._median(tokens_per_second)

        # Persist rollups
        rollups = []
        now = datetime.utcnow()
        for name, value in metrics.items():
            if value is not None:
                rollup = MetricRollup(
                    scope_type=RollupScopeType.SESSION,
                    scope_id=session_id,
                    metric_name=name,
                    metric_value=value,
                    computed_at=now,
                )
                await self.rollup_repo.upsert(self.session, rollup)
                rollups.append(rollup)

        logger.info(
            "Computed session rollups",
            session_id=str(session_id),
            metric_count=len(rollups),
        )

        return rollups

    async def compute_variant_rollups(self, variant_id: UUID) -> List[MetricRollup]:
        """Compute rollup metrics for a variant across all sessions.

        Args:
            variant_id: Variant to compute rollups for

        Returns:
            List of computed MetricRollup models
        """
        # Get all sessions for this variant
        result = await self.session.execute(
            select(SessionModel).where(SessionModel.variant_id == str(variant_id))
        )
        sessions = list(result.scalars().all())

        if not sessions:
            self._handle_empty_window(RollupScopeType.VARIANT, str(variant_id))
            return []

        # Get session-level rollups
        session_rollups = await self.session.execute(
            select(MetricRollupModel).where(
                MetricRollupModel.scope_type == RollupScopeType.SESSION,
                MetricRollupModel.scope_id.in_([s.session_id for s in sessions]),
            )
        )
        rollup_models = list(session_rollups.scalars().all())

        # Aggregate session-level metrics
        latencies = []
        ttfts = []
        durations = []
        success_count = 0

        for rm in rollup_models:
            if rm.metric_name == "median_latency_ms" and rm.metric_value:
                latencies.append(rm.metric_value)
            elif rm.metric_name == "median_ttft_ms" and rm.metric_value:
                ttfts.append(rm.metric_value)
        
        for s in sessions:
            if s.ended_at and s.started_at:
                duration = (s.ended_at - s.started_at).total_seconds() / 60.0
                durations.append(duration)
            if s.status.value in ["completed"]:
                success_count += 1

        success_rate = success_count / len(sessions) if sessions else 0.0

        metrics = {
            "session_count": float(len(sessions)),
            "session_success_rate": success_rate,
        }

        if latencies:
            metrics["median_latency_ms"] = self._median(latencies)
            metrics["p95_latency_ms"] = self._percentile(latencies, 95)
        
        if ttfts:
            metrics["median_ttft_ms"] = self._median(ttfts)
        
        if durations:
            metrics["median_session_duration_minutes"] = self._median(durations)

        # Persist
        rollups = []
        now = datetime.utcnow()
        for name, value in metrics.items():
            if value is not None:
                rollup = MetricRollup(
                    scope_type=RollupScopeType.VARIANT,
                    scope_id=variant_id,
                    metric_name=name,
                    metric_value=value,
                    computed_at=now,
                )
                await self.rollup_repo.upsert(self.session, rollup)
                rollups.append(rollup)

        logger.info(
            "Computed variant rollups",
            variant_id=str(variant_id),
            metric_count=len(rollups),
        )

        return rollups

    async def compute_experiment_rollups(self, experiment_id: UUID) -> List[MetricRollup]:
        """Compute rollup metrics for an experiment across all variants.

        Args:
            experiment_id: Experiment to compute rollups for

        Returns:
            List of computed MetricRollup models
        """
        # Get all sessions for this experiment
        result = await self.session.execute(
            select(SessionModel).where(SessionModel.experiment_id == str(experiment_id))
        )
        sessions = list(result.scalars().all())

        if not sessions:
            self._handle_empty_window(RollupScopeType.EXPERIMENT, str(experiment_id))
            return []

        # Get variant IDs
        variant_ids = list(set(s.variant_id for s in sessions))
        unique_variants = len(variant_ids)

        # Get all requests for this experiment
        req_result = await self.session.execute(
            select(RequestModel).where(RequestModel.experiment_id == str(experiment_id))
        )
        requests = list(req_result.scalars().all())

        # Aggregate
        latencies = [r.latency_ms for r in requests if r.latency_ms is not None]

        metrics = {
            "variant_count": float(unique_variants),
            "total_session_count": float(len(sessions)),
            "total_request_count": float(len(requests)),
        }

        if latencies:
            metrics["median_latency_ms"] = self._median(latencies)
            metrics["p95_latency_ms"] = self._percentile(latencies, 95)

        # Persist
        rollups = []
        now = datetime.utcnow()
        for name, value in metrics.items():
            if value is not None:
                rollup = MetricRollup(
                    scope_type=RollupScopeType.EXPERIMENT,
                    scope_id=experiment_id,
                    metric_name=name,
                    metric_value=value,
                    computed_at=now,
                )
                await self.rollup_repo.upsert(self.session, rollup)
                rollups.append(rollup)

        logger.info(
            "Computed experiment rollups",
            experiment_id=str(experiment_id),
            metric_count=len(rollups),
        )

        return rollups
