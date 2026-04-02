"""Repository for Artifact entities."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import Artifact as ArtifactORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
    SQLAlchemyRepository,
)


class SQLArtifactRepository(SQLAlchemyRepository[ArtifactORM]):
    """SQLAlchemy repository for Artifact entities.

    Artifacts are arbitrary files/data produced during a benchmark session
    or experiment. Provides CRUD operations with scope-based filtering.
    """

    def __init__(self, db_session: SQLAlchemySession) -> None:
        """Initialize the repository.

        Args:
            db_session: SQLAlchemy session for database operations.
        """
        super().__init__(db_session, ArtifactORM)

    async def get_by_id(self, id: UUID) -> ArtifactORM | None:
        """Retrieve an artifact by its ID.

        Args:
            id: The artifact UUID to retrieve.

        Returns:
            The artifact, or None if not found.
        """
        return self._session.get(ArtifactORM, id)

    async def create(self, entity: ArtifactORM) -> ArtifactORM:
        """Create a new artifact.

        Args:
            entity: The artifact entity to create.

        Returns:
            The created artifact with generated fields populated.

        Raises:
            DuplicateIdentifierError: If an artifact with the same ID exists.
            ReferentialIntegrityError: If session_id or experiment_id references
                a non-existent entity.
        """
        try:
            self._session.add(entity)
            self._session.flush()
            return entity
        except IntegrityError as e:
            self._session.rollback()
            error_msg = str(e).lower()

            # Check for duplicate identifier
            if "artifacts_pkey" in str(e) or "unique constraint" in error_msg:
                raise DuplicateIdentifierError(
                    f"Artifact with ID '{entity.id}' already exists"
                ) from e

            # Check for referential integrity violations
            if "foreign key constraint failed" in error_msg:
                if "session" in error_msg:
                    raise ReferentialIntegrityError(
                        f"Session '{entity.session_id}' does not exist"
                    ) from e
                if "experiment" in error_msg:
                    raise ReferentialIntegrityError(
                        f"Experiment '{entity.experiment_id}' does not exist"
                    ) from e
                raise ReferentialIntegrityError(
                    "Referenced entity does not exist for artifact"
                ) from e

            raise

    async def update(self, entity: ArtifactORM) -> ArtifactORM:
        """Update an existing artifact.

        Args:
            entity: The artifact entity to update.

        Returns:
            The updated artifact.

        Raises:
            ReferentialIntegrityError: If the update would violate referential integrity.
        """
        try:
            self._session.merge(entity)
            self._session.flush()
            return entity
        except IntegrityError as e:
            self._session.rollback()
            if "foreign key constraint failed" in str(e).lower():
                raise ReferentialIntegrityError("Update violates referential integrity") from e
            raise

    async def delete(self, id: UUID) -> bool:
        """Delete an artifact by its ID.

        Args:
            id: The UUID of the artifact to delete.

        Returns:
            True if deleted, False if not found.
        """
        return await super().delete(id)

    async def list_by_session(
        self, session_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[ArtifactORM]:
        """List all artifacts for a specific session.

        Args:
            session_id: The session UUID to filter by.
            limit: Maximum number of artifacts to return.
            offset: Number of artifacts to skip.

        Returns:
            List of artifacts for the session.
        """
        stmt = (
            select(ArtifactORM)
            .where(ArtifactORM.session_id == session_id)
            .limit(limit)
            .offset(offset)
        )
        result = self._session.execute(stmt).scalars().all()
        return list(result)

    async def list_by_experiment(
        self, experiment_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[ArtifactORM]:
        """List all artifacts for a specific experiment.

        Args:
            experiment_id: The experiment UUID to filter by.
            limit: Maximum number of artifacts to return.
            offset: Number of artifacts to skip.

        Returns:
            List of artifacts for the experiment.
        """
        stmt = (
            select(ArtifactORM)
            .where(ArtifactORM.experiment_id == experiment_id)
            .limit(limit)
            .offset(offset)
        )
        result = self._session.execute(stmt).scalars().all()
        return list(result)

    async def list_all_scoped(
        self,
        session_id: UUID | None = None,
        experiment_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ArtifactORM]:
        """List artifacts filtered by scope (session, experiment, or both).

        Args:
            session_id: Optional session UUID to filter by.
            experiment_id: Optional experiment UUID to filter by.
            limit: Maximum number of artifacts to return.
            offset: Number of artifacts to skip.

        Returns:
            List of matching artifacts.
        """
        stmt = select(ArtifactORM)

        if session_id is not None:
            stmt = stmt.where(ArtifactORM.session_id == session_id)
        if experiment_id is not None:
            stmt = stmt.where(ArtifactORM.experiment_id == experiment_id)

        stmt = stmt.limit(limit).offset(offset)
        result = self._session.execute(stmt).scalars().all()
        return list(result)

    async def list_by_type(
        self, artifact_type: str, limit: int = 100, offset: int = 0
    ) -> list[ArtifactORM]:
        """List artifacts by type.

        Args:
            artifact_type: The artifact type to filter by (e.g., 'export', 'report').
            limit: Maximum number of artifacts to return.
            offset: Number of artifacts to skip.

        Returns:
            List of matching artifacts.
        """
        stmt = (
            select(ArtifactORM)
            .where(ArtifactORM.artifact_type == artifact_type)
            .limit(limit)
            .offset(offset)
        )
        result = self._session.execute(stmt).scalars().all()
        return list(result)
