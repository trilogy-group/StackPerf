"""Integration tests for metric rollups."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.models import (
    Request,
    RequestStatus,
    MetricRollup,
    RollupScopeType,
    SessionStatus,
)
from benchmark_core.db.models import RequestModel, SessionModel
from benchmark_core.repositories.metric_rollup_repository import MetricRollupRepository
from collectors.rollups import MetricRollupService


class TestSessionRollups:
    """Tests for session-level rollups."""

    @pytest.mark.asyncio
    async def test_compute_session_rollups(
        self,
        db_session: AsyncSession,
        sample_session,
    ):
        """Should compute session rollups correctly."""
        from benchmark_core.repositories.request_repository import RequestRepository
        
        # Create some requests
        repo = RequestRepository()
        now = datetime.utcnow()
        
        for i in range(5):
            request = Request(
                session_id=sample_session.session_id,
                litellm_call_id=f"rollup-call-{i}",
                model="gpt-4",
                started_at=now - timedelta(minutes=i),
                latency_ms=100.0 + i * 50,
                input_tokens=100,
                output_tokens=50,
                status=RequestStatus.SUCCESS if i < 4 else RequestStatus.ERROR,
            )
            await repo.create(db_session, request)
        
        # Compute rollups
        service = MetricRollupService(db_session)
        rollups = await service.compute_session_rollups(sample_session.session_id)
        
        assert len(rollups) > 0
        
        # Verify metrics exist
        rollup_repo = MetricRollupRepository()
        session_rollups = await rollup_repo.get_by_session(
            db_session, str(sample_session.session_id)
        )
        
        metric_names = [r.metric_name for r in session_rollups]
        assert "request_count" in metric_names
        assert "success_count" in metric_names
        assert "error_count" in metric_names

    @pytest.mark.asyncio
    async def test_session_median_latency(
        self,
        db_session: AsyncSession,
        sample_session,
    ):
        """Should compute median latency correctly."""
        from benchmark_core.repositories.request_repository import RequestRepository
        
        repo = RequestRepository()
        now = datetime.utcnow()
        latencies = [100.0, 200.0, 300.0, 400.0, 500.0]
        
        for i, lat in enumerate(latencies):
            request = Request(
                session_id=sample_session.session_id,
                litellm_call_id=f"median-call-{i}",
                model="gpt-4",
                started_at=now,
                latency_ms=lat,
            )
            await repo.create(db_session, request)
        
        # Compute rollups
        service = MetricRollupService(db_session)
        await service.compute_session_rollups(sample_session.session_id)
        
        # Get median
        rollup_repo = MetricRollupRepository()
        median = await rollup_repo.get_by_scope_and_name(
            db_session,
            RollupScopeType.SESSION,
            str(sample_session.session_id),
            "median_latency_ms",
        )
        
        assert median is not None
        # Median of [100, 200, 300, 400, 500] is 300
        assert median.metric_value == 300.0


class TestEmptyWindowHandling:
    """Tests for empty window handling."""

    @pytest.mark.asyncio
    async def test_empty_session_returns_empty_rollups(
        self,
        db_session: AsyncSession,
        sample_session,
    ):
        """Should handle session with no requests gracefully."""
        service = MetricRollupService(db_session)
        
        # Session with no requests
        rollups = await service.compute_session_rollups(sample_session.session_id)
        
        # Should return empty list, not raise
        assert rollups == []

    @pytest.mark.asyncio
    async def test_empty_variant_returns_empty_rollups(
        self,
        db_session: AsyncSession,
        sample_variant,
    ):
        """Should handle variant with no sessions gracefully."""
        service = MetricRollupService(db_session)
        
        rollups = await service.compute_variant_rollups(sample_variant.variant_id)
        
        assert rollups == []


class TestRollupUpsert:
    """Tests for rollup upsert behavior."""

    @pytest.mark.asyncio
    async def test_upsert_creates_new(
        self,
        db_session: AsyncSession,
        sample_session,
    ):
        """Should create new rollup on first compute."""
        repo = MetricRollupRepository()
        
        rollup = MetricRollup(
            scope_type=RollupScopeType.SESSION,
            scope_id=sample_session.session_id,
            metric_name="test_metric",
            metric_value=42.0,
        )
        
        result = await repo.upsert(db_session, rollup)
        
        assert result.metric_value == 42.0

    @pytest.mark.asyncio
    async def test_upsert_updates_existing(
        self,
        db_session: AsyncSession,
        sample_session,
    ):
        """Should update existing rollup on recompute."""
        repo = MetricRollupRepository()
        
        # Create first
        rollup1 = MetricRollup(
            scope_type=RollupScopeType.SESSION,
            scope_id=sample_session.session_id,
            metric_name="test_metric",
            metric_value=42.0,
        )
        await repo.upsert(db_session, rollup1)
        
        # Update with same scope
        rollup2 = MetricRollup(
            scope_type=RollupScopeType.SESSION,
            scope_id=sample_session.session_id,
            metric_name="test_metric",
            metric_value=84.0,
        )
        result = await repo.upsert(db_session, rollup2)
        
        # Should update, not create duplicate
        rollups = await repo.get_by_session(db_session, str(sample_session.session_id))
        test_rollups = [r for r in rollups if r.metric_name == "test_metric"]
        
        assert len(test_rollups) == 1
        assert test_rollups[0].metric_value == 84.0
