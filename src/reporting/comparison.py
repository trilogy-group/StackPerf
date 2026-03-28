"""Comparison services for providers, models, harnesses, and configurations."""

import copy
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import (
    Experiment,
    ExperimentVariant,
    Variant,
)
from benchmark_core.db.models import (
    Request as RequestORM,
)
from benchmark_core.db.models import (
    Session as SessionORM,
)
from benchmark_core.models import MetricRollup, Session


class VariantComparison(BaseModel):
    """Comparison metrics for a single variant."""

    variant_id: UUID
    variant_name: str
    provider: str
    model: str
    harness_profile: str
    session_count: int = Field(default=0, description="Number of valid sessions")
    total_requests: int = Field(default=0, description="Total request count")
    avg_latency_ms: float | None = Field(default=None, description="Average latency in ms")
    avg_ttft_ms: float | None = Field(default=None, description="Average time to first token in ms")
    total_errors: int = Field(default=0, description="Total error count")
    error_rate: float = Field(default=0.0, description="Error rate (errors/requests)")
    cache_hit_rate: float | None = Field(default=None, description="Cache hit rate")


class ProviderComparison(BaseModel):
    """Comparison metrics aggregated by provider."""

    provider: str
    session_count: int = Field(default=0)
    total_requests: int = Field(default=0)
    avg_latency_ms: float | None = Field(default=None)
    avg_ttft_ms: float | None = Field(default=None)
    total_errors: int = Field(default=0)
    error_rate: float = Field(default=0.0)
    variant_count: int = Field(default=0, description="Number of variants using this provider")


class ModelComparison(BaseModel):
    """Comparison metrics aggregated by model."""

    provider: str
    model: str
    session_count: int = Field(default=0)
    total_requests: int = Field(default=0)
    avg_latency_ms: float | None = Field(default=None)
    avg_ttft_ms: float | None = Field(default=None)
    total_errors: int = Field(default=0)
    error_rate: float = Field(default=0.0)


class HarnessProfileComparison(BaseModel):
    """Comparison metrics aggregated by harness profile."""

    harness_profile: str
    session_count: int = Field(default=0)
    total_requests: int = Field(default=0)
    avg_latency_ms: float | None = Field(default=None)
    avg_ttft_ms: float | None = Field(default=None)
    total_errors: int = Field(default=0)
    error_rate: float = Field(default=0.0)
    variant_count: int = Field(default=0, description="Number of variants using this profile")


class ExperimentComparisonResult(BaseModel):
    """Complete comparison result for an experiment."""

    experiment_id: UUID
    experiment_name: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now())
    variants: list[VariantComparison] = Field(default_factory=list)
    providers: list[ProviderComparison] = Field(default_factory=list)
    models: list[ModelComparison] = Field(default_factory=list)
    harness_profiles: list[HarnessProfileComparison] = Field(default_factory=list)


class ComparisonService:
    """Service for generating benchmark comparisons.

    Provides experiment-level comparison queries and summary views
    by provider, model, harness profile, and variant.

    All queries exclude invalid sessions by default to ensure
    clean comparisons.
    """

    def __init__(self, db_session: SQLAlchemySession) -> None:
        """Initialize the comparison service.

        Args:
            db_session: SQLAlchemy database session for queries.
        """
        self._session = db_session

    async def compare_sessions(
        self,
        session_ids: list[UUID],
        include_invalid: bool = False,
    ) -> dict[str, Any]:
        """Compare metrics across multiple sessions.

        Args:
            session_ids: List of session UUIDs to compare.
            include_invalid: Whether to include sessions marked as invalid.

        Returns:
            Dictionary with session comparison data.
        """
        if not session_ids:
            return {"sessions": [], "summary": {}}

        # Build base query
        stmt = (
            select(
                SessionORM.id.label("session_id"),
                SessionORM.status,
                SessionORM.outcome_state,
                Variant.name.label("variant_name"),
                Variant.provider,
                Variant.model_alias,
                func.count(RequestORM.id).label("total_requests"),
                func.avg(RequestORM.latency_ms).label("avg_latency_ms"),
                func.avg(RequestORM.ttft_ms).label("avg_ttft_ms"),
                func.sum(case((RequestORM.error.is_(True), 1), else_=0)).label("total_errors"),
            )
            .select_from(SessionORM)
            .join(Variant, SessionORM.variant_id == Variant.id)
            .outerjoin(RequestORM, RequestORM.session_id == SessionORM.id)
            .where(SessionORM.id.in_(session_ids))
            .group_by(
                SessionORM.id,
                SessionORM.status,
                SessionORM.outcome_state,
                Variant.name,
                Variant.provider,
                Variant.model_alias,
            )
        )

        if not include_invalid:
            stmt = stmt.where(
                (SessionORM.outcome_state.is_(None)) | (SessionORM.outcome_state != "invalid")
            )

        results = self._session.execute(stmt).all()

        sessions = [
            {
                "session_id": str(row.session_id),
                "variant_name": row.variant_name,
                "provider": row.provider,
                "model": row.model_alias,
                "status": row.status,
                "outcome_state": row.outcome_state,
                "total_requests": row.total_requests or 0,
                "avg_latency_ms": row.avg_latency_ms,
                "avg_ttft_ms": row.avg_ttft_ms,
                "total_errors": row.total_errors or 0,
            }
            for row in results
        ]

        # Calculate summary statistics
        if sessions:
            total_requests = sum(s["total_requests"] for s in sessions)
            total_errors = sum(s["total_errors"] for s in sessions)
            latencies = [s["avg_latency_ms"] for s in sessions if s["avg_latency_ms"] is not None]
            ttfts = [s["avg_ttft_ms"] for s in sessions if s["avg_ttft_ms"] is not None]

            summary = {
                "session_count": len(sessions),
                "total_requests": total_requests,
                "total_errors": total_errors,
                "overall_error_rate": total_errors / total_requests if total_requests > 0 else 0.0,
                "overall_avg_latency_ms": sum(latencies) / len(latencies) if latencies else None,
                "overall_avg_ttft_ms": sum(ttfts) / len(ttfts) if ttfts else None,
            }
        else:
            summary = {
                "session_count": 0,
                "total_requests": 0,
                "total_errors": 0,
                "overall_error_rate": 0.0,
                "overall_avg_latency_ms": None,
                "overall_avg_ttft_ms": None,
            }

        return {"sessions": sessions, "summary": summary}

    async def compare_variants(
        self,
        experiment_id: UUID,
        include_invalid: bool = False,
        order_by: str = "variant_name",
        limit: int = 100,
    ) -> list[VariantComparison]:
        """Compare all variants within an experiment.

        Args:
            experiment_id: UUID of the experiment to analyze.
            include_invalid: Whether to include sessions marked as invalid.
            order_by: Field to order results by (default: variant_name).
            limit: Maximum number of variants to return.

        Returns:
            List of VariantComparison objects ordered deterministically.
        """
        # Verify experiment exists
        experiment = self._session.get(Experiment, experiment_id)
        if experiment is None:
            return []

        # Build query starting from ExperimentVariant to include all variants
        # even those with 0 sessions
        stmt = (
            select(
                Variant.id.label("variant_id"),
                Variant.name.label("variant_name"),
                Variant.provider,
                Variant.model_alias,
                Variant.harness_profile,
                func.count(func.distinct(SessionORM.id)).label("session_count"),
                func.count(RequestORM.id).label("total_requests"),
                func.avg(RequestORM.latency_ms).label("avg_latency_ms"),
                func.avg(RequestORM.ttft_ms).label("avg_ttft_ms"),
                func.sum(case((RequestORM.error.is_(True), 1), else_=0)).label("total_errors"),
            )
            .select_from(ExperimentVariant)
            .join(Variant, Variant.id == ExperimentVariant.variant_id)
            .outerjoin(SessionORM, SessionORM.variant_id == Variant.id)
            .outerjoin(RequestORM, RequestORM.session_id == SessionORM.id)
            .where(ExperimentVariant.experiment_id == experiment_id)
            .group_by(
                Variant.id,
                Variant.name,
                Variant.provider,
                Variant.model_alias,
                Variant.harness_profile,
            )
        )

        if not include_invalid:
            # Join condition for session filtering
            stmt = stmt.where(
                (SessionORM.id.is_(None))
                | (SessionORM.outcome_state.is_(None))
                | (SessionORM.outcome_state != "invalid")
            )

        # Apply deterministic ordering
        order_column = {
            "variant_name": Variant.name,
            "provider": Variant.provider,
            "model": Variant.model_alias,
            "session_count": func.count(func.distinct(SessionORM.id)),
            "avg_latency_ms": func.avg(RequestORM.latency_ms),
            "error_rate": func.sum(case((RequestORM.error.is_(True), 1), else_=0)),
        }.get(order_by, Variant.name)

        # Sort variant_name ascending, others descending for metrics
        if order_by in ["session_count", "avg_latency_ms", "error_rate"]:
            stmt = stmt.order_by(order_column.desc().nulls_last(), Variant.name.asc())
        else:
            stmt = stmt.order_by(order_column.asc(), Variant.name.asc())

        stmt = stmt.limit(limit)

        results = self._session.execute(stmt).all()

        comparisons = []
        for row in results:
            total_requests = row.total_requests or 0
            total_errors = row.total_errors or 0
            error_rate = total_errors / total_requests if total_requests > 0 else 0.0

            comparisons.append(
                VariantComparison(
                    variant_id=row.variant_id,
                    variant_name=row.variant_name,
                    provider=row.provider,
                    model=row.model_alias,
                    harness_profile=row.harness_profile,
                    session_count=row.session_count or 0,
                    total_requests=total_requests,
                    avg_latency_ms=row.avg_latency_ms,
                    avg_ttft_ms=row.avg_ttft_ms,
                    total_errors=total_errors,
                    error_rate=error_rate,
                )
            )

        return comparisons

    async def compare_providers(
        self,
        experiment_id: UUID,
        include_invalid: bool = False,
        order_by: str = "provider",
        limit: int = 100,
    ) -> list[ProviderComparison]:
        """Compare metrics across providers for an experiment.

        Args:
            experiment_id: UUID of the experiment to analyze.
            include_invalid: Whether to include sessions marked as invalid.
            order_by: Field to order results by.
            limit: Maximum number of providers to return.

        Returns:
            List of ProviderComparison objects ordered deterministically.
        """
        # Verify experiment exists
        experiment = self._session.get(Experiment, experiment_id)
        if experiment is None:
            return []

        # Build query aggregating by provider
        stmt = (
            select(
                Variant.provider,
                func.count(func.distinct(Variant.id)).label("variant_count"),
                func.count(func.distinct(SessionORM.id)).label("session_count"),
                func.count(RequestORM.id).label("total_requests"),
                func.avg(RequestORM.latency_ms).label("avg_latency_ms"),
                func.avg(RequestORM.ttft_ms).label("avg_ttft_ms"),
                func.sum(case((RequestORM.error.is_(True), 1), else_=0)).label("total_errors"),
            )
            .select_from(ExperimentVariant)
            .join(Variant, Variant.id == ExperimentVariant.variant_id)
            .outerjoin(SessionORM, SessionORM.variant_id == Variant.id)
            .outerjoin(RequestORM, RequestORM.session_id == SessionORM.id)
            .where(ExperimentVariant.experiment_id == experiment_id)
            .group_by(Variant.provider)
        )

        if not include_invalid:
            stmt = stmt.where(
                (SessionORM.id.is_(None))
                | (SessionORM.outcome_state.is_(None))
                | (SessionORM.outcome_state != "invalid")
            )

        # Apply deterministic ordering
        order_column = {
            "provider": Variant.provider,
            "session_count": func.count(func.distinct(SessionORM.id)),
            "avg_latency_ms": func.avg(RequestORM.latency_ms),
            "error_rate": func.sum(case((RequestORM.error.is_(True), 1), else_=0)),
        }.get(order_by, Variant.provider)

        if order_by in ["session_count", "avg_latency_ms", "error_rate"]:
            stmt = stmt.order_by(order_column.desc().nulls_last(), Variant.provider.asc())
        else:
            stmt = stmt.order_by(order_column.asc())

        stmt = stmt.limit(limit)

        results = self._session.execute(stmt).all()

        comparisons = []
        for row in results:
            total_requests = row.total_requests or 0
            total_errors = row.total_errors or 0
            error_rate = total_errors / total_requests if total_requests > 0 else 0.0

            comparisons.append(
                ProviderComparison(
                    provider=row.provider,
                    session_count=row.session_count or 0,
                    total_requests=total_requests,
                    avg_latency_ms=row.avg_latency_ms,
                    avg_ttft_ms=row.avg_ttft_ms,
                    total_errors=total_errors,
                    error_rate=error_rate,
                    variant_count=row.variant_count or 0,
                )
            )

        return comparisons

    async def compare_models(
        self,
        experiment_id: UUID,
        include_invalid: bool = False,
        order_by: str = "model",
        limit: int = 100,
    ) -> list[ModelComparison]:
        """Compare metrics across models for an experiment.

        Args:
            experiment_id: UUID of the experiment to analyze.
            include_invalid: Whether to include sessions marked as invalid.
            order_by: Field to order results by.
            limit: Maximum number of models to return.

        Returns:
            List of ModelComparison objects ordered deterministically.
        """
        # Verify experiment exists
        experiment = self._session.get(Experiment, experiment_id)
        if experiment is None:
            return []

        # Build query aggregating by provider + model
        stmt = (
            select(
                Variant.provider,
                Variant.model_alias,
                func.count(func.distinct(SessionORM.id)).label("session_count"),
                func.count(RequestORM.id).label("total_requests"),
                func.avg(RequestORM.latency_ms).label("avg_latency_ms"),
                func.avg(RequestORM.ttft_ms).label("avg_ttft_ms"),
                func.sum(case((RequestORM.error.is_(True), 1), else_=0)).label("total_errors"),
            )
            .select_from(ExperimentVariant)
            .join(Variant, Variant.id == ExperimentVariant.variant_id)
            .outerjoin(SessionORM, SessionORM.variant_id == Variant.id)
            .outerjoin(RequestORM, RequestORM.session_id == SessionORM.id)
            .where(ExperimentVariant.experiment_id == experiment_id)
            .group_by(Variant.provider, Variant.model_alias)
        )

        if not include_invalid:
            stmt = stmt.where(
                (SessionORM.id.is_(None))
                | (SessionORM.outcome_state.is_(None))
                | (SessionORM.outcome_state != "invalid")
            )

        # Apply deterministic ordering
        order_column = {
            "model": Variant.model_alias,
            "provider": Variant.provider,
            "session_count": func.count(func.distinct(SessionORM.id)),
            "avg_latency_ms": func.avg(RequestORM.latency_ms),
            "error_rate": func.sum(case((RequestORM.error.is_(True), 1), else_=0)),
        }.get(order_by, Variant.model_alias)

        if order_by in ["session_count", "avg_latency_ms", "error_rate"]:
            stmt = stmt.order_by(order_column.desc().nulls_last(), Variant.provider.asc(), Variant.model_alias.asc())
        else:
            stmt = stmt.order_by(order_column.asc(), Variant.provider.asc())

        stmt = stmt.limit(limit)

        results = self._session.execute(stmt).all()

        comparisons = []
        for row in results:
            total_requests = row.total_requests or 0
            total_errors = row.total_errors or 0
            error_rate = total_errors / total_requests if total_requests > 0 else 0.0

            comparisons.append(
                ModelComparison(
                    provider=row.provider,
                    model=row.model_alias,
                    session_count=row.session_count or 0,
                    total_requests=total_requests,
                    avg_latency_ms=row.avg_latency_ms,
                    avg_ttft_ms=row.avg_ttft_ms,
                    total_errors=total_errors,
                    error_rate=error_rate,
                )
            )

        return comparisons

    async def compare_harness_profiles(
        self,
        experiment_id: UUID,
        include_invalid: bool = False,
        order_by: str = "harness_profile",
        limit: int = 100,
    ) -> list[HarnessProfileComparison]:
        """Compare metrics across harness profiles for an experiment.

        Args:
            experiment_id: UUID of the experiment to analyze.
            include_invalid: Whether to include sessions marked as invalid.
            order_by: Field to order results by.
            limit: Maximum number of harness profiles to return.

        Returns:
            List of HarnessProfileComparison objects ordered deterministically.
        """
        # Verify experiment exists
        experiment = self._session.get(Experiment, experiment_id)
        if experiment is None:
            return []

        # Build query aggregating by harness_profile
        stmt = (
            select(
                Variant.harness_profile,
                func.count(func.distinct(Variant.id)).label("variant_count"),
                func.count(func.distinct(SessionORM.id)).label("session_count"),
                func.count(RequestORM.id).label("total_requests"),
                func.avg(RequestORM.latency_ms).label("avg_latency_ms"),
                func.avg(RequestORM.ttft_ms).label("avg_ttft_ms"),
                func.sum(case((RequestORM.error.is_(True), 1), else_=0)).label("total_errors"),
            )
            .select_from(ExperimentVariant)
            .join(Variant, Variant.id == ExperimentVariant.variant_id)
            .outerjoin(SessionORM, SessionORM.variant_id == Variant.id)
            .outerjoin(RequestORM, RequestORM.session_id == SessionORM.id)
            .where(ExperimentVariant.experiment_id == experiment_id)
            .group_by(Variant.harness_profile)
        )

        if not include_invalid:
            stmt = stmt.where(
                (SessionORM.id.is_(None))
                | (SessionORM.outcome_state.is_(None))
                | (SessionORM.outcome_state != "invalid")
            )

        # Apply deterministic ordering
        order_column = {
            "harness_profile": Variant.harness_profile,
            "session_count": func.count(func.distinct(SessionORM.id)),
            "avg_latency_ms": func.avg(RequestORM.latency_ms),
            "error_rate": func.sum(case((RequestORM.error.is_(True), 1), else_=0)),
        }.get(order_by, Variant.harness_profile)

        if order_by in ["session_count", "avg_latency_ms", "error_rate"]:
            stmt = stmt.order_by(order_column.desc().nulls_last(), Variant.harness_profile.asc())
        else:
            stmt = stmt.order_by(order_column.asc())

        stmt = stmt.limit(limit)

        results = self._session.execute(stmt).all()

        comparisons = []
        for row in results:
            total_requests = row.total_requests or 0
            total_errors = row.total_errors or 0
            error_rate = total_errors / total_requests if total_requests > 0 else 0.0

            comparisons.append(
                HarnessProfileComparison(
                    harness_profile=row.harness_profile,
                    session_count=row.session_count or 0,
                    total_requests=total_requests,
                    avg_latency_ms=row.avg_latency_ms,
                    avg_ttft_ms=row.avg_ttft_ms,
                    total_errors=total_errors,
                    error_rate=error_rate,
                    variant_count=row.variant_count or 0,
                )
            )

        return comparisons

    async def get_experiment_comparison(
        self,
        experiment_id: UUID,
        include_invalid: bool = False,
    ) -> ExperimentComparisonResult | None:
        """Get complete comparison data for an experiment.

        This is a convenience method that aggregates all comparison views
        (variants, providers, models, harness profiles) in a single call.

        Args:
            experiment_id: UUID of the experiment to analyze.
            include_invalid: Whether to include sessions marked as invalid.

        Returns:
            ExperimentComparisonResult with all comparison data, or None if
            experiment doesn't exist.
        """
        experiment = self._session.get(Experiment, experiment_id)
        if experiment is None:
            return None

        variants = await self.compare_variants(experiment_id, include_invalid)
        providers = await self.compare_providers(experiment_id, include_invalid)
        models = await self.compare_models(experiment_id, include_invalid)
        harness_profiles = await self.compare_harness_profiles(experiment_id, include_invalid)

        return ExperimentComparisonResult(
            experiment_id=experiment_id,
            experiment_name=experiment.name,
            variants=variants,
            providers=providers,
            models=models,
            harness_profiles=harness_profiles,
        )


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
        return copy.deepcopy(self._data)
