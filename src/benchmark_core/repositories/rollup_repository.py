"""Repository for MetricRollup persistence."""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import MetricRollup as MetricRollupORM
from benchmark_core.models import MetricRollup
from benchmark_core.repositories.base import SQLAlchemyRepository


class SQLRollupRepository(SQLAlchemyRepository[MetricRollupORM]):
    """SQLAlchemy repository for MetricRollup persistence.

    Provides CRUD operations for metric rollups with dimension-based
    querying capabilities.
    """

    def __init__(self, session: SQLAlchemySession) -> None:
        """Initialize repository with database session.

        Args:
            session: SQLAlchemy session for database operations.
        """
        super().__init__(session, MetricRollupORM)

    def _to_orm(self, model: MetricRollup) -> MetricRollupORM:
        """Convert domain model to ORM entity.

        Args:
            model: Domain MetricRollup model.

        Returns:
            SQLAlchemy ORM entity.
        """
        return MetricRollupORM(
            id=model.rollup_id,
            dimension_type=model.dimension_type,
            dimension_id=model.dimension_id,
            metric_name=model.metric_name,
            metric_value=model.metric_value,
            sample_count=model.sample_count,
            computed_at=model.computed_at,
        )

    def _to_domain(self, orm: MetricRollupORM) -> MetricRollup:
        """Convert ORM entity to domain model.

        Args:
            orm: SQLAlchemy ORM entity.

        Returns:
            Domain MetricRollup model.
        """
        return MetricRollup(
            rollup_id=orm.id,
            dimension_type=orm.dimension_type,
            dimension_id=orm.dimension_id,
            metric_name=orm.metric_name,
            metric_value=orm.metric_value,
            sample_count=orm.sample_count,
            computed_at=orm.computed_at,
        )

    def create_rollup(self, rollup: MetricRollup) -> MetricRollup:
        """Create a single metric rollup.

        Args:
            rollup: Domain MetricRollup model to persist.

        Returns:
            Created MetricRollup domain model.
        """
        orm = self._to_orm(rollup)
        self._session.add(orm)
        self._session.flush()
        return self._to_domain(orm)

    def create_many(self, rollups: list[MetricRollup]) -> list[MetricRollup]:
        """Bulk create metric rollups.

        Note: This operation is NOT idempotent - it will fail if rollups with
        the same IDs already exist. For true idempotency, use upsert operations
        or handle conflicts explicitly.

        Args:
            rollups: List of MetricRollup domain models to persist.

        Returns:
            List of created MetricRollup domain models.
        """
        if not rollups:
            return []

        orm_entities = [self._to_orm(r) for r in rollups]
        self._session.add_all(orm_entities)
        self._session.flush()
        return [self._to_domain(orm) for orm in orm_entities]

    def get_by_dimension(
        self,
        dimension_type: str,
        dimension_id: str,
    ) -> list[MetricRollup]:
        """Get all rollups for a specific dimension.

        Args:
            dimension_type: Type of dimension (request, session, variant, experiment).
            dimension_id: ID of the dimension.

        Returns:
            List of MetricRollup domain models for the dimension.
        """
        stmt = select(MetricRollupORM).where(
            MetricRollupORM.dimension_type == dimension_type,
            MetricRollupORM.dimension_id == dimension_id,
        )
        result = self._session.execute(stmt)
        orm_entities = result.scalars().all()
        return [self._to_domain(orm) for orm in orm_entities]

    def get_by_dimension_and_metric(
        self,
        dimension_type: str,
        dimension_id: str,
        metric_name: str,
    ) -> MetricRollup | None:
        """Get a specific rollup by dimension and metric name.

        Args:
            dimension_type: Type of dimension.
            dimension_id: ID of the dimension.
            metric_name: Name of the metric.

        Returns:
            MetricRollup if found, None otherwise.
        """
        stmt = select(MetricRollupORM).where(
            MetricRollupORM.dimension_type == dimension_type,
            MetricRollupORM.dimension_id == dimension_id,
            MetricRollupORM.metric_name == metric_name,
        )
        result = self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    def get_session_rollups(self, session_id: UUID) -> list[MetricRollup]:
        """Get all rollups for a session.

        Args:
            session_id: Session UUID.

        Returns:
            List of session-level MetricRollups.
        """
        return self.get_by_dimension("session", str(session_id))

    def get_variant_rollups(self, variant_id: str) -> list[MetricRollup]:
        """Get all rollups for a variant.

        Args:
            variant_id: Variant identifier.

        Returns:
            List of variant-level MetricRollups.
        """
        return self.get_by_dimension("variant", variant_id)

    def get_experiment_rollups(self, experiment_id: str) -> list[MetricRollup]:
        """Get all rollups for an experiment.

        Args:
            experiment_id: Experiment identifier.

        Returns:
            List of experiment-level MetricRollups.
        """
        return self.get_by_dimension("experiment", experiment_id)

    def delete_by_dimension(
        self,
        dimension_type: str,
        dimension_id: str,
    ) -> int:
        """Delete all rollups for a dimension.

        Args:
            dimension_type: Type of dimension.
            dimension_id: ID of the dimension.

        Returns:
            Number of records deleted.
        """
        stmt = delete(MetricRollupORM).where(
            MetricRollupORM.dimension_type == dimension_type,
            MetricRollupORM.dimension_id == dimension_id,
        )
        result = self._session.execute(stmt)
        return result.rowcount
