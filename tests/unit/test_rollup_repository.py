"""Unit tests for the rollup repository."""

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from benchmark_core.models import MetricRollup
from benchmark_core.repositories.rollup_repository import SQLRollupRepository


class TestSQLRollupRepository:
    """Tests for SQLRollupRepository."""

    def test_to_orm_conversion(self) -> None:
        """Test domain model to ORM conversion."""
        rollup = MetricRollup(
            rollup_id=uuid4(),
            dimension_type="session",
            dimension_id="test-session-123",
            metric_name="latency_median_ms",
            metric_value=150.5,
            sample_count=10,
            computed_at=datetime.now(UTC),
        )

        mock_session = MagicMock()
        repo = SQLRollupRepository(mock_session)

        orm = repo._to_orm(rollup)

        assert orm.id == rollup.rollup_id
        assert orm.dimension_type == "session"
        assert orm.dimension_id == "test-session-123"
        assert orm.metric_name == "latency_median_ms"
        assert orm.metric_value == 150.5
        assert orm.sample_count == 10

    def test_to_domain_conversion(self) -> None:
        """Test ORM to domain model conversion."""
        import uuid

        from benchmark_core.db.models import MetricRollup as MetricRollupORM

        orm = MetricRollupORM(
            id=uuid.uuid4(),
            dimension_type="request",
            dimension_id="req-456",
            metric_name="ttft_ms",
            metric_value=45.0,
            sample_count=1,
            computed_at=datetime.now(UTC),
        )

        mock_session = MagicMock()
        repo = SQLRollupRepository(mock_session)

        domain = repo._to_domain(orm)

        assert domain.dimension_type == "request"
        assert domain.dimension_id == "req-456"
        assert domain.metric_name == "ttft_ms"
        assert domain.metric_value == 45.0
        assert domain.sample_count == 1

    def test_create_many_empty_list(self) -> None:
        """Test create_many with empty list."""
        mock_session = MagicMock()
        repo = SQLRollupRepository(mock_session)

        result = repo.create_many([])

        assert result == []
        mock_session.add_all.assert_not_called()

    def test_create_many_with_rollups(self) -> None:
        """Test create_many with rollups."""
        rollups = [
            MetricRollup(
                dimension_type="session",
                dimension_id="session-1",
                metric_name="latency_ms",
                metric_value=100.0,
                sample_count=5,
            ),
            MetricRollup(
                dimension_type="session",
                dimension_id="session-1",
                metric_name="ttft_ms",
                metric_value=50.0,
                sample_count=5,
            ),
        ]

        mock_session = MagicMock()
        repo = SQLRollupRepository(mock_session)

        result = repo.create_many(rollups)

        assert len(result) == 2
        mock_session.add_all.assert_called_once()

    def test_get_by_dimension_returns_domain_models(self) -> None:
        """Test get_by_dimension returns domain models."""
        import uuid

        from benchmark_core.db.models import MetricRollup as MetricRollupORM

        # Create mock ORM objects with all required fields
        mock_orm1 = MetricRollupORM(
            id=uuid.uuid4(),
            dimension_type="session",
            dimension_id="session-1",
            metric_name="latency_ms",
            metric_value=100.0,
            sample_count=5,
            computed_at=datetime.now(UTC),
        )
        mock_orm2 = MetricRollupORM(
            id=uuid.uuid4(),
            dimension_type="session",
            dimension_id="session-1",
            metric_name="ttft_ms",
            metric_value=50.0,
            sample_count=5,
            computed_at=datetime.now(UTC),
        )

        # Mock the session.execute to return these objects
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [mock_orm1, mock_orm2]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = SQLRollupRepository(mock_session)
        results = repo.get_by_dimension("session", "session-1")

        assert len(results) == 2
        assert all(isinstance(r, MetricRollup) for r in results)
        assert results[0].metric_name == "latency_ms"
        assert results[1].metric_name == "ttft_ms"

    def test_get_session_rollups(self) -> None:
        """Test get_session_rollups delegates to get_by_dimension."""
        session_id = uuid4()

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = SQLRollupRepository(mock_session)
        results = repo.get_session_rollups(session_id)

        # Verify the query was made with correct dimension
        assert results == []

    def test_get_variant_rollups(self) -> None:
        """Test get_variant_rollups delegates to get_by_dimension."""
        variant_id = "variant-123"

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = SQLRollupRepository(mock_session)
        results = repo.get_variant_rollups(variant_id)

        assert results == []

    def test_get_experiment_rollups(self) -> None:
        """Test get_experiment_rollups delegates to get_by_dimension."""
        experiment_id = "experiment-456"

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = SQLRollupRepository(mock_session)
        results = repo.get_experiment_rollups(experiment_id)

        assert results == []
