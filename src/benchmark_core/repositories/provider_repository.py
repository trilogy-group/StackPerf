"""Repository for Provider entities."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import Provider as ProviderORM
from benchmark_core.db.models import ProviderModel as ProviderModelORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    SQLAlchemyRepository,
)


class SQLProviderRepository(SQLAlchemyRepository[ProviderORM]):
    """SQLAlchemy repository for Provider entities.

    Provides CRUD operations with referential integrity enforcement.
    Models can be loaded with or without their provider relationship.
    """

    def __init__(self, db_session: SQLAlchemySession) -> None:
        """Initialize the repository.

        Args:
            db_session: SQLAlchemy session for database operations.
        """
        super().__init__(db_session, ProviderORM)

    async def get_by_name(self, name: str) -> ProviderORM | None:
        """Retrieve a provider by its unique name.

        Args:
            name: The provider name to search for.

        Returns:
            The provider if found, None otherwise.
        """
        stmt = select(ProviderORM).where(ProviderORM.name == name)
        return self._session.execute(stmt).scalar_one_or_none()

    async def create(self, entity: ProviderORM) -> ProviderORM:
        """Create a new provider.

        Args:
            entity: The provider entity to create.

        Returns:
            The created provider with generated fields populated.

        Raises:
            DuplicateIdentifierError: If a provider with the same name exists.
        """
        try:
            self._session.add(entity)
            self._session.flush()
            return entity
        except IntegrityError as e:
            self._session.rollback()
            if "providers_name_key" in str(e) or "UNIQUE constraint failed" in str(e):
                raise DuplicateIdentifierError(
                    f"Provider with name '{entity.name}' already exists"
                ) from e
            raise

    async def create_with_models(
        self, provider: ProviderORM, models: list[ProviderModelORM]
    ) -> ProviderORM:
        """Create a provider with its associated models atomically.

        Args:
            provider: The provider entity to create.
            models: List of provider model entities to associate.

        Returns:
            The created provider with models populated.

        Raises:
            DuplicateIdentifierError: If a provider with the same name exists
                or if any model alias conflicts.
        """
        try:
            self._session.add(provider)
            # Models are added via cascade from the relationship
            provider.models = models
            self._session.flush()
            return provider
        except IntegrityError as e:
            self._session.rollback()
            if "providers_name_key" in str(e) or "UNIQUE constraint failed" in str(e):
                raise DuplicateIdentifierError(
                    f"Provider with name '{provider.name}' already exists"
                ) from e
            if "provider_models" in str(e):
                raise DuplicateIdentifierError(
                    f"Model alias conflict for provider '{provider.name}'"
                ) from e
            raise

    async def update(self, entity: ProviderORM) -> ProviderORM:
        """Update an existing provider.

        Args:
            entity: The provider entity to update.

        Returns:
            The updated provider.
        """
        self._session.merge(entity)
        self._session.flush()
        return entity

    async def delete(self, id: UUID) -> bool:
        """Delete a provider by its ID.

        Cascades to delete associated provider models.

        Args:
            id: The UUID of the provider to delete.

        Returns:
            True if deleted, False if not found.
        """
        # Cascading delete is handled by the ORM relationship
        return await super().delete(id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[ProviderORM]:
        """List all providers with their models loaded.

        Args:
            limit: Maximum number of providers to return.
            offset: Number of providers to skip.

        Returns:
            List of providers with models populated.
        """
        from sqlalchemy.orm import joinedload

        stmt = (
            select(ProviderORM).options(joinedload(ProviderORM.models)).limit(limit).offset(offset)
        )
        result = self._session.execute(stmt).scalars().unique().all()
        return list(result)
