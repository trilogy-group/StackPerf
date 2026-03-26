"""Repository for Request entities."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import Request as RequestORM
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
    SQLAlchemyRepository,
)


class SQLRequestRepository(SQLAlchemyRepository[RequestORM]):
    """SQLAlchemy repository for Request entities.

    Requests are one normalized LLM call observed through LiteLLM.
    Provides idempotent creation and batch operations.
    """

    def __init__(self, db_session: SQLAlchemySession) -> None:
        """Initialize the repository.

        Args:
            db_session: SQLAlchemy session for database operations.
        """
        super().__init__(db_session, RequestORM)

    async def get_by_request_id(self, request_id: str) -> RequestORM | None:
        """Retrieve a request by its LiteLLM request ID.

        Args:
            request_id: The LiteLLM call ID to search for.

        Returns:
            The request if found, None otherwise.
        """
        stmt = select(RequestORM).where(RequestORM.request_id == request_id)
        return self._session.execute(stmt).scalars().one_or_none()

    async def create(self, entity: RequestORM) -> RequestORM:
        """Create a new request.

        Args:
            entity: The request entity to create.

        Returns:
            The created request with generated fields populated.

        Raises:
            DuplicateIdentifierError: If a request with the same LiteLLM ID exists.
            ReferentialIntegrityError: If the session does not exist.
        """
        try:
            self._session.add(entity)
            self._session.flush()
            return entity
        except IntegrityError as e:
            self._session.rollback()
            error_msg = str(e).lower()

            # Check for duplicate request ID
            if "requests_request_id_key" in str(e) or "unique constraint" in error_msg:
                raise DuplicateIdentifierError(
                    f"Request with ID '{entity.request_id}' already exists"
                ) from e

            # Check for referential integrity violations
            if "foreign key constraint failed" in error_msg:
                raise ReferentialIntegrityError(
                    f"Session '{entity.session_id}' does not exist"
                ) from e

            raise

    async def create_many(self, requests: list[RequestORM]) -> list[RequestORM]:
        """Create multiple request records (idempotent).

        If any request already exists, it is skipped (not treated as an error).
        This method is designed for bulk ingestion from collectors.

        Args:
            requests: List of request entities to create.

        Returns:
            List of successfully created requests. Duplicates are omitted.
        """
        if not requests:
            return []

        created: list[RequestORM] = []
        skipped = 0

        for request in requests:
            # Check if request already exists (idempotent behavior)
            existing = await self.get_by_request_id(request.request_id)
            if existing is not None:
                skipped += 1
                continue

            self._session.add(request)
            created.append(request)

        if created:
            try:
                self._session.flush()
            except IntegrityError:
                # Rollback on IntegrityError to maintain session consistency
                self._session.rollback()
                return []

        return created

    async def create_many_strict(self, requests: list[RequestORM]) -> list[RequestORM]:
        """Create multiple request records with strict validation.

        Unlike create_many, this method will fail fast on any error
        and provide detailed error information.

        Args:
            requests: List of request entities to create.

        Returns:
            List of created requests.

        Raises:
            DuplicateIdentifierError: If any request ID already exists.
            ReferentialIntegrityError: If any session does not exist.
        """
        if not requests:
            return []

        try:
            for request in requests:
                self._session.add(request)
            self._session.flush()
            return requests
        except IntegrityError as e:
            self._session.rollback()
            error_msg = str(e).lower()

            if "requests_request_id_key" in str(e) or "unique constraint" in error_msg:
                raise DuplicateIdentifierError(
                    "One or more requests already exist in batch"
                ) from e

            if "foreign key constraint failed" in error_msg:
                raise ReferentialIntegrityError(
                    "One or more sessions referenced in batch do not exist"
                ) from e

            raise

    async def update(self, entity: RequestORM) -> RequestORM:
        """Update an existing request.

        Note: Requests are generally immutable after creation.
        This method exists for correcting ingestion errors.

        Args:
            entity: The request entity to update.

        Returns:
            The updated request.
        """
        self._session.merge(entity)
        self._session.flush()
        return entity

    async def get_by_session(
        self, session_id: UUID, limit: int = 1000, offset: int = 0
    ) -> list[RequestORM]:
        """Get all requests for a session.

        Args:
            session_id: The session UUID to filter by.
            limit: Maximum number of requests to return.
            offset: Number of requests to skip.

        Returns:
            List of requests for the session, ordered by timestamp.
        """
        stmt = (
            select(RequestORM)
            .where(RequestORM.session_id == session_id)
            .order_by(RequestORM.timestamp)
            .limit(limit)
            .offset(offset)
        )
        result = self._session.execute(stmt).scalars().all()
        return list(result)

    async def get_by_session_and_time_range(
        self,
        session_id: UUID,
        start_time: str,
        end_time: str,
        limit: int = 1000,
    ) -> list[RequestORM]:
        """Get requests for a session within a time range.

        Args:
            session_id: The session UUID to filter by.
            start_time: Start of time range (ISO format).
            end_time: End of time range (ISO format).
            limit: Maximum number of requests to return.

        Returns:
            List of requests in the time range.
        """
        from datetime import datetime

        stmt = (
            select(RequestORM)
            .where(
                RequestORM.session_id == session_id,
                RequestORM.timestamp >= datetime.fromisoformat(start_time),
                RequestORM.timestamp <= datetime.fromisoformat(end_time),
            )
            .order_by(RequestORM.timestamp)
            .limit(limit)
        )
        result = self._session.execute(stmt).scalars().all()
        return list(result)

    async def count_by_session(self, session_id: UUID) -> int:
        """Count total requests for a session.

        Args:
            session_id: The session UUID.

        Returns:
            Number of requests for the session.
        """
        from sqlalchemy import func

        stmt = (
            select(func.count()).select_from(RequestORM).where(RequestORM.session_id == session_id)
        )
        result = self._session.execute(stmt).scalar()
        return result or 0

    async def delete(self, id: UUID) -> bool:
        """Delete a request by its ID.

        Args:
            id: The UUID of the request to delete.

        Returns:
            True if deleted, False if not found.
        """
        return await super().delete(id)

    async def delete_by_session(self, session_id: UUID) -> int:
        """Delete all requests for a session.

        This is used for session cleanup/administrative purposes.

        Args:
            session_id: The session UUID.

        Returns:
            Number of requests deleted.
        """
        from sqlalchemy import delete

        stmt = delete(RequestORM).where(RequestORM.session_id == session_id)
        result = self._session.execute(stmt)
        self._session.flush()
        return result.rowcount
