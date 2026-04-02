"""Repository for Experiment entities."""

from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import (
    Experiment as ExperimentORM,
)
from benchmark_core.db.models import (
    ExperimentVariant as ExperimentVariantORM,
)
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
    SQLAlchemyRepository,
)


class SQLExperimentRepository(SQLAlchemyRepository[ExperimentORM]):
    """SQLAlchemy repository for Experiment entities.

    Experiments are named comparison groupings that contain one or more variants.
    """

    def __init__(self, db_session: SQLAlchemySession) -> None:
        """Initialize the repository.

        Args:
            db_session: SQLAlchemy session for database operations.
        """
        super().__init__(db_session, ExperimentORM)

    async def get_by_name(self, name: str) -> ExperimentORM | None:
        """Retrieve an experiment by its unique name.

        Args:
            name: The experiment name to search for.

        Returns:
            The experiment if found, None otherwise.
        """
        stmt = select(ExperimentORM).where(ExperimentORM.name == name)
        return self._session.execute(stmt).scalar_one_or_none()

    async def create(self, entity: ExperimentORM) -> ExperimentORM:
        """Create a new experiment.

        Args:
            entity: The experiment entity to create.

        Returns:
            The created experiment with generated fields populated.

        Raises:
            DuplicateIdentifierError: If an experiment with the same name exists.
        """
        try:
            self._session.add(entity)
            self._session.flush()
            return entity
        except IntegrityError as e:
            self._session.rollback()
            if "experiments_name_key" in str(e) or "UNIQUE constraint failed" in str(e):
                raise DuplicateIdentifierError(
                    f"Experiment with name '{entity.name}' already exists"
                ) from e
            raise

    async def create_with_variants(
        self, experiment: ExperimentORM, variant_ids: list[UUID]
    ) -> ExperimentORM:
        """Create an experiment with associated variants atomically.

        Args:
            experiment: The experiment entity to create.
            variant_ids: List of variant UUIDs to associate with the experiment.

        Returns:
            The created experiment with variant associations.

        Raises:
            DuplicateIdentifierError: If an experiment with the same name exists.
            ReferentialIntegrityError: If any variant ID does not exist.
        """
        try:
            self._session.add(experiment)
            self._session.flush()  # Get the experiment ID

            # Create experiment-variant associations
            for variant_id in variant_ids:
                assoc = ExperimentVariantORM(
                    experiment_id=experiment.id,
                    variant_id=variant_id,
                )
                self._session.add(assoc)

            self._session.flush()
            return experiment
        except IntegrityError as e:
            self._session.rollback()
            if "experiments_name_key" in str(e) or "UNIQUE constraint failed" in str(e):
                raise DuplicateIdentifierError(
                    f"Experiment with name '{experiment.name}' already exists"
                ) from e
            if "FOREIGN KEY constraint failed" in str(e):
                raise ReferentialIntegrityError(
                    f"One or more variant IDs do not exist: {variant_ids}"
                ) from e
            raise

    async def update(self, entity: ExperimentORM) -> ExperimentORM:
        """Update an existing experiment.

        Args:
            entity: The experiment entity to update.

        Returns:
            The updated experiment.
        """
        self._session.merge(entity)
        self._session.flush()
        return entity

    async def add_variant(self, experiment_id: UUID, variant_id: UUID) -> None:
        """Add a variant to an existing experiment.

        Args:
            experiment_id: The experiment ID.
            variant_id: The variant ID to add.

        Raises:
            DuplicateIdentifierError: If the variant is already in the experiment.
            ReferentialIntegrityError: If the experiment or variant does not exist.
        """
        assoc = ExperimentVariantORM(
            experiment_id=experiment_id,
            variant_id=variant_id,
        )
        try:
            self._session.add(assoc)
            self._session.flush()
        except IntegrityError as e:
            self._session.rollback()
            if "uq_experiment_variant" in str(e) or "UNIQUE constraint failed" in str(e):
                raise DuplicateIdentifierError(
                    f"Variant {variant_id} is already in experiment {experiment_id}"
                ) from e
            if "FOREIGN KEY constraint failed" in str(e):
                raise ReferentialIntegrityError(
                    f"Experiment {experiment_id} or variant {variant_id} does not exist"
                ) from e
            raise

    async def remove_variant(self, experiment_id: UUID, variant_id: UUID) -> bool:
        """Remove a variant from an experiment.

        Args:
            experiment_id: The experiment ID.
            variant_id: The variant ID to remove.

        Returns:
            True if removed, False if the association did not exist.
        """
        from sqlalchemy import delete

        stmt = delete(ExperimentVariantORM).where(
            ExperimentVariantORM.experiment_id == experiment_id,
            ExperimentVariantORM.variant_id == variant_id,
        )
        result = cast(CursorResult, self._session.execute(stmt))
        self._session.flush()
        return result.rowcount > 0

    async def delete(self, id: UUID) -> bool:
        """Delete an experiment by its ID.

        Note: Experiments referenced by active sessions cannot be deleted
        due to RESTRICT ondelete behavior in the schema.

        Args:
            id: The UUID of the experiment to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            ReferentialIntegrityError: If the experiment is referenced by existing sessions.
        """
        try:
            return await super().delete(id)  # type: ignore[no-any-return]
        except IntegrityError as e:
            self._session.rollback()
            if "FOREIGN KEY constraint failed" in str(e) or "sessions" in str(e):
                raise ReferentialIntegrityError(
                    f"Cannot delete experiment {id}: referenced by existing sessions"
                ) from e
            raise

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[ExperimentORM]:
        """List all experiments with their variant associations.

        Args:
            limit: Maximum number of experiments to return.
            offset: Number of experiments to skip.

        Returns:
            List of experiments with variants populated.
        """
        from sqlalchemy.orm import joinedload

        stmt = (
            select(ExperimentORM)
            .options(joinedload(ExperimentORM.experiment_variants))
            .limit(limit)
            .offset(offset)
        )
        result = self._session.execute(stmt).scalars().unique().all()
        return list(result)

    async def get_with_variants(self, id: UUID) -> ExperimentORM | None:
        """Get an experiment with all its variants eagerly loaded.

        Args:
            id: The experiment ID.

        Returns:
            The experiment with variants populated, or None if not found.
        """
        from sqlalchemy.orm import joinedload

        stmt = (
            select(ExperimentORM)
            .where(ExperimentORM.id == id)
            .options(joinedload(ExperimentORM.experiment_variants))
        )
        return self._session.execute(stmt).scalars().unique().one_or_none()
