"""Service for managing TaskCard entities."""

from uuid import UUID

from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import TaskCard as TaskCardORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
    RepositoryError,
)
from benchmark_core.repositories.task_card_repository import SQLTaskCardRepository


class TaskCardServiceError(Exception):
    """Raised when task card service operation fails."""

    pass


class TaskCardService:
    """Service for managing task card definitions.

    Task cards define the benchmark task used for comparable sessions:
    - Goal and starting prompt
    - Stop conditions
    - Timebox limits
    - Repository context
    """

    def __init__(
        self,
        db_session: SQLAlchemySession,
        task_card_repo: SQLTaskCardRepository | None = None,
    ) -> None:
        """Initialize the task card service.

        Args:
            db_session: SQLAlchemy session for database operations.
            task_card_repo: Optional repository instance. If not provided, one is created.
        """
        self._db_session = db_session
        self._task_card_repo = task_card_repo or SQLTaskCardRepository(db_session)

    async def create_task_card(
        self,
        name: str,
        goal: str,
        starting_prompt: str,
        stop_condition: str,
        repo_path: str | None = None,
        session_timebox_minutes: int | None = None,
        notes: list[str] | None = None,
    ) -> TaskCardORM:
        """Create a new task card.

        Args:
            name: Unique task card name.
            goal: The task goal description.
            starting_prompt: The initial prompt given to the harness.
            stop_condition: The condition that indicates task completion.
            repo_path: Optional repository path for context.
            session_timebox_minutes: Optional session time limit in minutes.
            notes: Optional list of notes.

        Returns:
            The created task card.

        Raises:
            TaskCardServiceError: If validation fails or task card already exists.
        """
        if not name:
            raise TaskCardServiceError("name is required")
        if not goal:
            raise TaskCardServiceError("goal is required")
        if not starting_prompt:
            raise TaskCardServiceError("starting_prompt is required")
        if not stop_condition:
            raise TaskCardServiceError("stop_condition is required")

        task_card = TaskCardORM(
            name=name,
            goal=goal,
            starting_prompt=starting_prompt,
            stop_condition=stop_condition,
            repo_path=repo_path,
            session_timebox_minutes=session_timebox_minutes,
            notes=notes or [],
        )

        try:
            return await self._task_card_repo.create(task_card)
        except DuplicateIdentifierError as e:
            raise TaskCardServiceError(f"TaskCard already exists: {e}") from e
        except RepositoryError as e:
            raise TaskCardServiceError(f"Failed to create task card: {e}") from e

    async def get_task_card(self, task_card_id: UUID) -> TaskCardORM | None:
        """Retrieve a task card by ID.

        Args:
            task_card_id: The task card UUID.

        Returns:
            The task card, or None if not found.
        """
        return await self._task_card_repo.get_by_id(task_card_id)

    async def get_task_card_by_name(self, name: str) -> TaskCardORM | None:
        """Retrieve a task card by name.

        Args:
            name: The task card name.

        Returns:
            The task card, or None if not found.
        """
        return await self._task_card_repo.get_by_name(name)

    async def update_task_card(
        self,
        task_card_id: UUID,
        **updates: dict,
    ) -> TaskCardORM | None:
        """Update an existing task card.

        Args:
            task_card_id: The task card UUID.
            **updates: Fields to update.

        Returns:
            The updated task card, or None if not found.

        Raises:
            TaskCardServiceError: If the update would violate constraints.
        """
        task_card = await self._task_card_repo.get_by_id(task_card_id)
        if task_card is None:
            return None

        # Apply updates
        allowed_fields = {
            "name",
            "goal",
            "starting_prompt",
            "stop_condition",
            "repo_path",
            "session_timebox_minutes",
            "notes",
        }

        for field, value in updates.items():
            if field in allowed_fields and hasattr(task_card, field):
                setattr(task_card, field, value)

        try:
            return await self._task_card_repo.update(task_card)
        except DuplicateIdentifierError as e:
            raise TaskCardServiceError(f"Update would create duplicate: {e}") from e
        except RepositoryError as e:
            raise TaskCardServiceError(f"Failed to update task card: {e}") from e

    async def delete_task_card(self, task_card_id: UUID) -> bool:
        """Delete a task card by ID.

        Note: Task cards referenced by sessions cannot be deleted.

        Args:
            task_card_id: The task card UUID.

        Returns:
            True if deleted, False if not found.

        Raises:
            TaskCardServiceError: If the task card is referenced by sessions.
        """
        try:
            return await self._task_card_repo.delete(task_card_id)  # type: ignore[no-any-return]
        except ReferentialIntegrityError as e:
            raise TaskCardServiceError(
                "Cannot delete task card: referenced by existing sessions"
            ) from e

    async def list_task_cards(self, limit: int = 100, offset: int = 0) -> list[TaskCardORM]:
        """List all task cards.

        Args:
            limit: Maximum number of task cards to return.
            offset: Number of task cards to skip.

        Returns:
            List of task cards.
        """
        return await self._task_card_repo.list_all(limit, offset)  # type: ignore[no-any-return]

    async def search_task_cards_by_goal(self, query: str, limit: int = 20) -> list[TaskCardORM]:
        """Search task cards by goal text.

        Args:
            query: The search query.
            limit: Maximum number of results.

        Returns:
            List of matching task cards.
        """
        return await self._task_card_repo.search_by_goal(query, limit)  # type: ignore[no-any-return]

    async def add_note_to_task_card(self, task_card_id: UUID, note: str) -> TaskCardORM | None:
        """Add a note to an existing task card.

        Args:
            task_card_id: The task card UUID.
            note: The note to add.

        Returns:
            The updated task card, or None if not found.
        """
        task_card = await self._task_card_repo.get_by_id(task_card_id)
        if task_card is None:
            return None

        notes = list(task_card.notes or [])
        notes.append(note)
        task_card.notes = notes

        try:
            return await self._task_card_repo.update(task_card)
        except RepositoryError as e:
            raise TaskCardServiceError(f"Failed to add note: {e}") from e

    async def validate_task_card_exists(self, task_card_id: UUID) -> bool:
        """Check if a task card exists.

        Args:
            task_card_id: The task card UUID.

        Returns:
            True if the task card exists.
        """
        return await self._task_card_repo.exists(task_card_id)  # type: ignore[no-any-return]
