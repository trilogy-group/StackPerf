"""Service for managing Experiment entities."""

from uuid import UUID

from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import Experiment as ExperimentORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
    RepositoryError,
)
from benchmark_core.repositories.experiment_repository import SQLExperimentRepository


class ExperimentServiceError(Exception):
    """Raised when experiment service operation fails."""

    pass


class ExperimentService:
    """Service for managing benchmark experiments.

    Experiments are named comparison groupings that contain one or more variants.
    They enable structured comparison of different configurations.
    """

    def __init__(
        self,
        db_session: SQLAlchemySession,
        experiment_repo: SQLExperimentRepository | None = None,
    ) -> None:
        """Initialize the experiment service.

        Args:
            db_session: SQLAlchemy session for database operations.
            experiment_repo: Optional repository instance. If not provided, one is created.
        """
        self._db_session = db_session
        self._experiment_repo = experiment_repo or SQLExperimentRepository(db_session)

    async def create_experiment(
        self,
        name: str,
        description: str = "",
        variant_ids: list[UUID] | None = None,
    ) -> ExperimentORM:
        """Create a new experiment with optional variant associations.

        Args:
            name: Unique experiment name.
            description: Optional experiment description.
            variant_ids: Optional list of variant UUIDs to associate.

        Returns:
            The created experiment with variant associations.

        Raises:
            ExperimentServiceError: If validation fails or experiment already exists.
        """
        if not name:
            raise ExperimentServiceError("name is required")

        experiment = ExperimentORM(
            name=name,
            description=description,
        )

        try:
            if variant_ids:
                return await self._experiment_repo.create_with_variants(experiment, variant_ids)
            return await self._experiment_repo.create(experiment)
        except DuplicateIdentifierError as e:
            raise ExperimentServiceError(f"Experiment already exists: {e}") from e
        except ReferentialIntegrityError as e:
            raise ExperimentServiceError(f"Invalid variant reference: {e}") from e
        except RepositoryError as e:
            raise ExperimentServiceError(f"Failed to create experiment: {e}") from e

    async def get_experiment(self, experiment_id: UUID) -> ExperimentORM | None:
        """Retrieve an experiment by ID.

        Args:
            experiment_id: The experiment UUID.

        Returns:
            The experiment, or None if not found.
        """
        return await self._experiment_repo.get_by_id(experiment_id)

    async def get_experiment_by_name(self, name: str) -> ExperimentORM | None:
        """Retrieve an experiment by name.

        Args:
            name: The experiment name.

        Returns:
            The experiment, or None if not found.
        """
        return await self._experiment_repo.get_by_name(name)

    async def get_experiment_with_variants(self, experiment_id: UUID) -> ExperimentORM | None:
        """Retrieve an experiment with all variants loaded.

        Args:
            experiment_id: The experiment UUID.

        Returns:
            The experiment with variants populated, or None if not found.
        """
        return await self._experiment_repo.get_with_variants(experiment_id)

    async def update_experiment(
        self,
        experiment_id: UUID,
        **updates: dict,
    ) -> ExperimentORM | None:
        """Update an existing experiment.

        Args:
            experiment_id: The experiment UUID.
            **updates: Fields to update (name, description).

        Returns:
            The updated experiment, or None if not found.

        Raises:
            ExperimentServiceError: If the update would violate constraints.
        """
        experiment = await self._experiment_repo.get_by_id(experiment_id)
        if experiment is None:
            return None

        # Apply updates
        allowed_fields = {"name", "description"}

        for field, value in updates.items():
            if field in allowed_fields and hasattr(experiment, field):
                setattr(experiment, field, value)

        try:
            return await self._experiment_repo.update(experiment)
        except DuplicateIdentifierError as e:
            raise ExperimentServiceError(f"Update would create duplicate: {e}") from e
        except RepositoryError as e:
            raise ExperimentServiceError(f"Failed to update experiment: {e}") from e

    async def delete_experiment(self, experiment_id: UUID) -> bool:
        """Delete an experiment by ID.

        Note: Experiments referenced by sessions cannot be deleted.

        Args:
            experiment_id: The experiment UUID.

        Returns:
            True if deleted, False if not found.

        Raises:
            ExperimentServiceError: If the experiment is referenced by sessions.
        """
        try:
            return await self._experiment_repo.delete(experiment_id)  # type: ignore[no-any-return]
        except ReferentialIntegrityError as e:
            raise ExperimentServiceError(
                "Cannot delete experiment: referenced by existing sessions"
            ) from e

    async def add_variant_to_experiment(self, experiment_id: UUID, variant_id: UUID) -> None:
        """Add a variant to an existing experiment.

        Args:
            experiment_id: The experiment UUID.
            variant_id: The variant UUID to add.

        Raises:
            ExperimentServiceError: If the variant is already in the experiment
                or if either entity does not exist.
        """
        try:
            await self._experiment_repo.add_variant(experiment_id, variant_id)
        except DuplicateIdentifierError as e:
            raise ExperimentServiceError(f"Variant already in experiment: {e}") from e
        except ReferentialIntegrityError as e:
            raise ExperimentServiceError(f"Invalid experiment or variant: {e}") from e

    async def remove_variant_from_experiment(self, experiment_id: UUID, variant_id: UUID) -> bool:
        """Remove a variant from an experiment.

        Args:
            experiment_id: The experiment UUID.
            variant_id: The variant UUID to remove.

        Returns:
            True if removed, False if the association did not exist.
        """
        return await self._experiment_repo.remove_variant(experiment_id, variant_id)  # type: ignore[no-any-return]

    async def list_experiments(self, limit: int = 100, offset: int = 0) -> list[ExperimentORM]:
        """List all experiments.

        Args:
            limit: Maximum number of experiments to return.
            offset: Number of experiments to skip.

        Returns:
            List of experiments with variants populated.
        """
        return await self._experiment_repo.list_all(limit, offset)  # type: ignore[no-any-return]

    async def get_experiment_variant_ids(self, experiment_id: UUID) -> list[UUID]:
        """Get the list of variant IDs in an experiment.

        Args:
            experiment_id: The experiment UUID.

        Returns:
            List of variant UUIDs, or empty list if experiment not found.
        """
        experiment = await self.get_experiment_with_variants(experiment_id)
        if experiment is None:
            return []

        return [assoc.variant_id for assoc in experiment.experiment_variants]

    async def validate_experiment_has_variants(self, experiment_id: UUID) -> bool:
        """Check if an experiment has at least one variant.

        Args:
            experiment_id: The experiment UUID.

        Returns:
            True if the experiment exists and has at least one variant.
        """
        experiment = await self.get_experiment_with_variants(experiment_id)
        if experiment is None:
            return False
        return len(experiment.experiment_variants) > 0
