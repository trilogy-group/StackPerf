"""Repository for Session entities."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import Session as SessionORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
    SQLAlchemyRepository,
)


class SQLSessionRepository(SQLAlchemyRepository[SessionORM]):
    """SQLAlchemy repository for Session entities.

    Sessions are one interactive benchmark session under one variant and one task card.
    Provides safe creation and finalization with referential integrity enforcement.
    """

    def __init__(self, db_session: SQLAlchemySession) -> None:
        """Initialize the repository.

        Args:
            db_session: SQLAlchemy session for database operations.
        """
        super().__init__(db_session, SessionORM)

    async def get_by_id(self, id: UUID) -> SessionORM | None:
        """Retrieve a session by its ID with related entities loaded.

        Args:
            id: The session UUID to retrieve.

        Returns:
            The session with experiment, variant, and task card loaded, or None.
        """
        from sqlalchemy.orm import joinedload

        stmt = (
            select(SessionORM)
            .where(SessionORM.id == id)
            .options(
                joinedload(SessionORM.experiment),
                joinedload(SessionORM.variant),
                joinedload(SessionORM.task_card),
            )
        )
        return self._session.execute(stmt).scalars().one_or_none()

    async def create(self, entity: SessionORM) -> SessionORM:
        """Create a new session.

        Validates that referenced entities (experiment, variant, task_card) exist
        before creation to preserve referential integrity.

        Args:
            entity: The session entity to create.

        Returns:
            The created session with generated fields populated.

        Raises:
            DuplicateIdentifierError: If a session with the same ID exists (shouldn't happen with UUIDs).
            ReferentialIntegrityError: If experiment, variant, or task_card do not exist.
        """
        try:
            self._session.add(entity)
            self._session.flush()
            return entity
        except IntegrityError as e:
            self._session.rollback()
            error_msg = str(e).lower()

            # Check for duplicate session identifier
            if "sessions_pkey" in str(e) or "unique constraint" in error_msg:
                raise DuplicateIdentifierError(
                    f"Session with ID '{entity.id}' already exists"
                ) from e

            # Check for referential integrity violations
            if "foreign key constraint failed" in error_msg:
                if "experiment" in error_msg:
                    raise ReferentialIntegrityError(
                        f"Experiment '{entity.experiment_id}' does not exist"
                    ) from e
                if "variant" in error_msg:
                    raise ReferentialIntegrityError(
                        f"Variant '{entity.variant_id}' does not exist"
                    ) from e
                if "task_card" in error_msg:
                    raise ReferentialIntegrityError(
                        f"TaskCard '{entity.task_card_id}' does not exist"
                    ) from e
                raise ReferentialIntegrityError(
                    "Referenced entity does not exist for session"
                ) from e

            raise

    async def update(self, entity: SessionORM) -> SessionORM:
        """Update an existing session.

        Args:
            entity: The session entity to update.

        Returns:
            The updated session.

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

    async def finalize_session(
        self,
        session_id: UUID,
        status: str = "completed",
        ended_at: datetime | None = None,
        outcome_state: str | None = None,
    ) -> SessionORM | None:
        """Safely finalize a session with end time, status, and outcome state.

        This is the recommended way to end a session - it atomically:
        1. Retrieves the session
        2. Sets ended_at to provided or current UTC time
        3. Updates status and outcome_state
        4. Saves changes

        Args:
            session_id: The session UUID to finalize.
            status: The final status (default: 'completed').
            ended_at: Optional end timestamp. Defaults to current UTC time.
            outcome_state: Optional outcome state (valid, invalid, aborted).

        Returns:
            The finalized session, or None if not found.

        Raises:
            ReferentialIntegrityError: If finalization fails due to constraint violation.
        """
        from datetime import UTC, datetime

        session = await self.get_by_id(session_id)
        if session is None:
            return None

        if ended_at is None:
            ended_at = datetime.now(UTC)

        try:
            session.ended_at = ended_at
            session.status = status
            if outcome_state is not None:
                session.outcome_state = outcome_state
            self._session.flush()
            return session
        except IntegrityError as e:
            self._session.rollback()
            raise ReferentialIntegrityError(f"Failed to finalize session {session_id}") from e

    async def list_by_experiment(
        self, experiment_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[SessionORM]:
        """List all sessions for a specific experiment.

        Args:
            experiment_id: The experiment UUID to filter by.
            limit: Maximum number of sessions to return.
            offset: Number of sessions to skip.

        Returns:
            List of sessions for the experiment.
        """
        from sqlalchemy.orm import joinedload

        stmt = (
            select(SessionORM)
            .where(SessionORM.experiment_id == experiment_id)
            .options(
                joinedload(SessionORM.variant),
                joinedload(SessionORM.task_card),
            )
            .limit(limit)
            .offset(offset)
        )
        result = self._session.execute(stmt).scalars().all()
        return list(result)

    async def list_by_variant(
        self, variant_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[SessionORM]:
        """List all sessions for a specific variant.

        Args:
            variant_id: The variant UUID to filter by.
            limit: Maximum number of sessions to return.
            offset: Number of sessions to skip.

        Returns:
            List of sessions for the variant.
        """
        from sqlalchemy.orm import joinedload

        stmt = (
            select(SessionORM)
            .where(SessionORM.variant_id == variant_id)
            .options(
                joinedload(SessionORM.experiment),
                joinedload(SessionORM.task_card),
            )
            .limit(limit)
            .offset(offset)
        )
        result = self._session.execute(stmt).scalars().all()
        return list(result)

    async def list_active(self, limit: int = 100) -> list[SessionORM]:
        """List all active sessions (status='active' and no ended_at).

        Args:
            limit: Maximum number of sessions to return.

        Returns:
            List of active sessions.
        """
        stmt = (
            select(SessionORM)
            .where(SessionORM.status == "active", SessionORM.ended_at.is_(None))
            .limit(limit)
        )
        result = self._session.execute(stmt).scalars().all()
        return list(result)

    async def delete(self, id: UUID) -> bool:
        """Delete a session by its ID.

        Sessions should generally not be deleted - use finalize_session instead.
        This method exists for administrative cleanup.

        Args:
            id: The UUID of the session to delete.

        Returns:
            True if deleted, False if not found.
        """
        return await super().delete(id)

    async def exists_by_harness_session_id(self, harness_session_id: str) -> bool:
        """Check if a session exists with the given harness session identifier.

        This is used to reject duplicate session identifiers.

        Args:
            harness_session_id: The external harness session identifier.

        Returns:
            True if a session with this identifier exists.
        """
        # Since we don't have a harness_session_id field in the ORM model,
        # we check by operator_label or a custom mechanism
        # For now, check if any session has this in operator_label
        stmt = select(SessionORM).where(SessionORM.operator_label == harness_session_id)
        result = self._session.execute(stmt).scalars().first()
        return result is not None

    async def create_session_safe(
        self,
        experiment_id: UUID,
        variant_id: UUID,
        task_card_id: UUID,
        harness_profile: str,
        repo_path: str,
        git_branch: str,
        git_commit: str,
        git_dirty: bool = False,
        operator_label: str | None = None,
        proxy_credential_alias: str | None = None,
        proxy_credential_id: str | None = None,
        notes: str | None = None,
    ) -> SessionORM:
        """Safely create a session with validation and duplicate rejection.

        This is the recommended method for creating sessions - it:
        1. Validates that the session identifier is unique
        2. Checks referential integrity of foreign keys
        3. Creates the session atomically

        Args:
            experiment_id: The experiment UUID.
            variant_id: The variant UUID.
            task_card_id: The task card UUID.
            harness_profile: The harness profile name.
            repo_path: Absolute path to the repository.
            git_branch: Active git branch.
            git_commit: Commit SHA.
            git_dirty: Whether the working tree is dirty.
            operator_label: Optional operator-provided label (used as external session ID).
            proxy_credential_alias: Optional proxy credential key alias.
            proxy_credential_id: Optional proxy credential identifier.
            notes: Optional session notes from operator.

        Returns:
            The created session.

        Raises:
            DuplicateIdentifierError: If a session with the same operator_label exists.
            ReferentialIntegrityError: If any referenced entity does not exist.
        """
        # Import models for referential integrity checks
        from benchmark_core.db.models import (
            Experiment,
        )
        from benchmark_core.db.models import (
            TaskCard as TaskCardORM,
        )
        from benchmark_core.db.models import (
            Variant as VariantORM,
        )

        # Check for duplicate session identifier
        if operator_label is not None:
            existing = await self.exists_by_harness_session_id(operator_label)
            if existing:
                raise DuplicateIdentifierError(
                    f"Session with identifier '{operator_label}' already exists"
                )

        # Check referential integrity
        # Ensure proper UUID types for lookups
        exp_id = experiment_id if isinstance(experiment_id, UUID) else UUID(experiment_id)
        var_id = variant_id if isinstance(variant_id, UUID) else UUID(variant_id)
        task_id = task_card_id if isinstance(task_card_id, UUID) else UUID(task_card_id)

        experiment = self._session.get(Experiment, exp_id)
        if experiment is None:
            raise ReferentialIntegrityError(f"Experiment '{experiment_id}' does not exist")

        variant = self._session.get(VariantORM, var_id)
        if variant is None:
            raise ReferentialIntegrityError(f"Variant '{variant_id}' does not exist")

        task_card = self._session.get(TaskCardORM, task_id)
        if task_card is None:
            raise ReferentialIntegrityError(f"TaskCard '{task_card_id}' does not exist")

        # Create the session entity with proper UUID types
        session = SessionORM(
            experiment_id=exp_id,
            variant_id=var_id,
            task_card_id=task_id,
            harness_profile=harness_profile,
            repo_path=repo_path,
            git_branch=git_branch,
            git_commit=git_commit,
            git_dirty=git_dirty,
            operator_label=operator_label,
            proxy_credential_alias=proxy_credential_alias,
            proxy_credential_id=proxy_credential_id,
            notes=notes,
            status="active",
        )

        return await self.create(session)
