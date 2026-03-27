"""Base repository classes and interfaces."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session as SQLAlchemySession

T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    """Abstract base for all repositories.

    Provides common CRUD operations with referential integrity guarantees.
    """

    @abstractmethod
    async def get_by_id(self, id: UUID) -> T | None:
        """Retrieve an entity by its ID.

        Args:
            id: The UUID of the entity to retrieve.

        Returns:
            The entity if found, None otherwise.
        """
        ...

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity.

        Args:
            entity: The entity to create.

        Returns:
            The created entity with generated fields populated.

        Raises:
            DuplicateIdentifierError: If an entity with the same unique identifier exists.
        """
        ...

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity.

        Args:
            entity: The entity to update.

        Returns:
            The updated entity.

        Raises:
            EntityNotFoundError: If the entity does not exist.
        """
        ...

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete an entity by its ID.

        Args:
            id: The UUID of the entity to delete.

        Returns:
            True if deleted, False if not found.
        """
        ...

    @abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """List all entities with pagination.

        Args:
            limit: Maximum number of entities to return.
            offset: Number of entities to skip.

        Returns:
            List of entities.
        """
        ...


class RepositoryError(Exception):
    """Base exception for repository operations."""

    pass


class DuplicateIdentifierError(RepositoryError):
    """Raised when attempting to create an entity with a duplicate unique identifier."""

    pass


class EntityNotFoundError(RepositoryError):
    """Raised when attempting to update or access a non-existent entity."""

    pass


class ReferentialIntegrityError(RepositoryError):
    """Raised when an operation would violate referential integrity."""

    pass


class SQLAlchemyRepository(AbstractRepository[T], Generic[T]):
    """Base SQLAlchemy repository implementation.

    Provides common database operations with proper transaction handling
    and referential integrity enforcement.
    """

    def __init__(self, db_session: SQLAlchemySession, model_class: type[T]) -> None:
        """Initialize the repository.

        Args:
            db_session: SQLAlchemy session for database operations.
            model_class: The ORM model class this repository manages.
        """
        self._session = db_session
        self._model_class = model_class

    async def get_by_id(self, id: UUID) -> T | None:
        """Retrieve an entity by its ID."""
        return self._session.get(self._model_class, id)

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        self._session.add(entity)
        self._session.flush()
        return entity

    async def update(self, entity: T) -> T:
        """Update an existing entity."""
        self._session.merge(entity)
        self._session.flush()
        return entity

    async def delete(self, id: UUID) -> bool:
        """Delete an entity by its ID."""
        entity = await self.get_by_id(id)
        if entity is None:
            return False
        self._session.delete(entity)
        self._session.flush()
        return True

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """List all entities with pagination."""
        result = self._session.query(self._model_class).limit(limit).offset(offset).all()
        return list(result)

    async def exists(self, id: UUID) -> bool:
        """Check if an entity exists by its ID.

        Args:
            id: The UUID to check.

        Returns:
            True if the entity exists, False otherwise.
        """
        entity = await self.get_by_id(id)
        return entity is not None
