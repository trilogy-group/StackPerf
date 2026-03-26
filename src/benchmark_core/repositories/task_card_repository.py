"""Repository for TaskCard entities."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import TaskCard as TaskCardORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
    SQLAlchemyRepository,
)


class SQLTaskCardRepository(SQLAlchemyRepository[TaskCardORM]):
    """SQLAlchemy repository for TaskCard entities.

    Task cards define the benchmark task used for comparable sessions.
    """

    def __init__(self, db_session: SQLAlchemySession) -> None:
        """Initialize the repository.

        Args:
            db_session: SQLAlchemy session for database operations.
        """
        super().__init__(db_session, TaskCardORM)

    async def get_by_name(self, name: str) -> TaskCardORM | None:
        """Retrieve a task card by its unique name.

        Args:
            name: The task card name to search for.

        Returns:
            The task card if found, None otherwise.
        """
        stmt = select(TaskCardORM).where(TaskCardORM.name == name)
        return self._session.execute(stmt).scalar_one_or_none()

    async def create(self, entity: TaskCardORM) -> TaskCardORM:
        """Create a new task card.

        Args:
            entity: The task card entity to create.

        Returns:
            The created task card with generated fields populated.

        Raises:
            DuplicateIdentifierError: If a task card with the same name exists.
        """
        try:
            self._session.add(entity)
            self._session.flush()
            return entity
        except IntegrityError as e:
            self._session.rollback()
            if "task_cards_name_key" in str(e) or "UNIQUE constraint failed" in str(e):
                raise DuplicateIdentifierError(
                    f"TaskCard with name '{entity.name}' already exists"
                ) from e
            raise

    async def update(self, entity: TaskCardORM) -> TaskCardORM:
        """Update an existing task card.

        Args:
            entity: The task card entity to update.

        Returns:
            The updated task card.
        """
        self._session.merge(entity)
        self._session.flush()
        return entity

    async def delete(self, id: UUID) -> bool:
        """Delete a task card by its ID.

        Note: Task cards referenced by active sessions cannot be deleted
        due to RESTRICT ondelete behavior in the schema.

        Args:
            id: The UUID of the task card to delete.

        Returns:
            True if deleted, False if not found.

        Raises:
            ReferentialIntegrityError: If the task card is referenced by existing sessions.
        """
        try:
            return await super().delete(id)
        except IntegrityError as e:
            self._session.rollback()
            if "FOREIGN KEY constraint failed" in str(e) or "sessions" in str(e):
                raise ReferentialIntegrityError(
                    f"Cannot delete task card {id}: referenced by existing sessions"
                ) from e
            raise

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[TaskCardORM]:
        """List all task cards with pagination.

        Args:
            limit: Maximum number of task cards to return.
            offset: Number of task cards to skip.

        Returns:
            List of task cards.
        """
        return await super().list_all(limit, offset)

    async def search_by_goal(self, query: str, limit: int = 20) -> list[TaskCardORM]:
        """Search task cards by goal text.

        Args:
            query: The search query to match against goals.
            limit: Maximum number of results to return.

        Returns:
            List of matching task cards.
        """
        stmt = select(TaskCardORM).where(TaskCardORM.goal.ilike(f"%{query}%")).limit(limit)
        result = self._session.execute(stmt).scalars().all()
        return list(result)
