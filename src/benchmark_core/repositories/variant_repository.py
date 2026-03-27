"""Repository for Variant entities."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import Variant as VariantORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
    SQLAlchemyRepository,
)


class SQLVariantRepository(SQLAlchemyRepository[VariantORM]):
    """SQLAlchemy repository for Variant entities.

    Variants define benchmarkable combinations of provider, model,
    harness profile, and settings.
    """

    def __init__(self, db_session: SQLAlchemySession) -> None:
        """Initialize the repository.

        Args:
            db_session: SQLAlchemy session for database operations.
        """
        super().__init__(db_session, VariantORM)

    async def get_by_name(self, name: str) -> VariantORM | None:
        """Retrieve a variant by its unique name.

        Args:
            name: The variant name to search for.

        Returns:
            The variant if found, None otherwise.
        """
        stmt = select(VariantORM).where(VariantORM.name == name)
        return self._session.execute(stmt).scalar_one_or_none()

    async def create(self, entity: VariantORM) -> VariantORM:
        """Create a new variant.

        Args:
            entity: The variant entity to create.

        Returns:
            The created variant with generated fields populated.

        Raises:
            DuplicateIdentifierError: If a variant with the same name exists.
        """
        try:
            self._session.add(entity)
            self._session.flush()
            return entity
        except IntegrityError as e:
            self._session.rollback()
            if "variants_name_key" in str(e) or "UNIQUE constraint failed" in str(e):
                raise DuplicateIdentifierError(
                    f"Variant with name '{entity.name}' already exists"
                ) from e
            raise

    async def update(self, entity: VariantORM) -> VariantORM:
        """Update an existing variant.

        Args:
            entity: The variant entity to update.

        Returns:
            The updated variant.
        """
        self._session.merge(entity)
        self._session.flush()
        return entity

    async def delete(self, id: UUID) -> bool:
        """Delete a variant by its ID.

        Note: Variants referenced by active sessions cannot be deleted
        due to RESTRICT ondelete behavior in the schema.

        Args:
            id: The UUID of the variant to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            ReferentialIntegrityError: If the variant is referenced by existing sessions.
        """
        try:
            return await super().delete(id)
        except IntegrityError as e:
            self._session.rollback()
            if "FOREIGN KEY constraint failed" in str(e) or "sessions" in str(e):
                raise ReferentialIntegrityError(
                    f"Cannot delete variant {id}: referenced by existing sessions"
                ) from e
            raise

    async def list_by_provider(self, provider_name: str, limit: int = 100) -> list[VariantORM]:
        """List all variants for a specific provider.

        Args:
            provider_name: The provider name to filter by.
            limit: Maximum number of variants to return.

        Returns:
            List of variants for the specified provider.
        """
        stmt = select(VariantORM).where(VariantORM.provider == provider_name).limit(limit)
        result = self._session.execute(stmt).scalars().all()
        return list(result)

    async def list_by_harness_profile(
        self, profile_name: str, limit: int = 100
    ) -> list[VariantORM]:
        """List all variants using a specific harness profile.

        Args:
            profile_name: The harness profile name to filter by.
            limit: Maximum number of variants to return.

        Returns:
            List of variants using the specified harness profile.
        """
        stmt = select(VariantORM).where(VariantORM.harness_profile == profile_name).limit(limit)
        result = self._session.execute(stmt).scalars().all()
        return list(result)
