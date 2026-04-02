"""Repository for HarnessProfile entities."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import HarnessProfile as HarnessProfileORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    SQLAlchemyRepository,
)


class SQLHarnessProfileRepository(SQLAlchemyRepository[HarnessProfileORM]):
    """SQLAlchemy repository for HarnessProfile entities.

    Harness profiles define how a harness is configured to talk to the proxy.
    """

    def __init__(self, db_session: SQLAlchemySession) -> None:
        """Initialize the repository.

        Args:
            db_session: SQLAlchemy session for database operations.
        """
        super().__init__(db_session, HarnessProfileORM)

    async def get_by_name(self, name: str) -> HarnessProfileORM | None:
        """Retrieve a harness profile by its unique name.

        Args:
            name: The harness profile name to search for.

        Returns:
            The harness profile if found, None otherwise.
        """
        stmt = select(HarnessProfileORM).where(HarnessProfileORM.name == name)
        return self._session.execute(stmt).scalar_one_or_none()

    async def create(self, entity: HarnessProfileORM) -> HarnessProfileORM:
        """Create a new harness profile.

        Args:
            entity: The harness profile entity to create.

        Returns:
            The created harness profile with generated fields populated.

        Raises:
            DuplicateIdentifierError: If a harness profile with the same name exists.
        """
        try:
            self._session.add(entity)
            self._session.flush()
            return entity
        except IntegrityError as e:
            self._session.rollback()
            if "harness_profiles_name_key" in str(e) or "UNIQUE constraint failed" in str(e):
                raise DuplicateIdentifierError(
                    f"HarnessProfile with name '{entity.name}' already exists"
                ) from e
            raise

    async def update(self, entity: HarnessProfileORM) -> HarnessProfileORM:
        """Update an existing harness profile.

        Args:
            entity: The harness profile entity to update.

        Returns:
            The updated harness profile.
        """
        self._session.merge(entity)
        self._session.flush()
        return entity

    async def delete(self, id: UUID) -> bool:
        """Delete a harness profile by its ID.

        Args:
            id: The UUID of the harness profile to delete.

        Returns:
            True if deleted, False if not found.
        """
        return await super().delete(id)  # type: ignore[no-any-return]

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[HarnessProfileORM]:
        """List all harness profiles with pagination.

        Args:
            limit: Maximum number of harness profiles to return.
            offset: Number of harness profiles to skip.

        Returns:
            List of harness profiles.
        """
        return await super().list_all(limit, offset)  # type: ignore[no-any-return]

    async def list_by_protocol(self, protocol: str, limit: int = 100) -> list[HarnessProfileORM]:
        """List all harness profiles for a specific protocol surface.

        Args:
            protocol: The protocol surface to filter by (e.g., 'anthropic_messages', 'openai_responses').
            limit: Maximum number of profiles to return.

        Returns:
            List of harness profiles using the specified protocol.
        """
        stmt = (
            select(HarnessProfileORM)
            .where(HarnessProfileORM.protocol_surface == protocol)
            .limit(limit)
        )
        result = self._session.execute(stmt).scalars().all()
        return list(result)
