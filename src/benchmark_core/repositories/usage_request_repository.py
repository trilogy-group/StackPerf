"""Repository for UsageRequest entities."""

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, inspect, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import UsageRequest as UsageRequestORM
from benchmark_core.repositories.base import SQLAlchemyRepository


class SQLUsageRequestRepository(SQLAlchemyRepository[UsageRequestORM]):
    """SQLAlchemy repository for UsageRequest entities.

    Provides idempotent bulk creation and lookup helpers for usage records.
    No prompt or response content is stored by default.
    """

    def __init__(self, db_session: SQLAlchemySession) -> None:
        """Initialize the repository.

        Args:
            db_session: SQLAlchemy session for database operations.
        """
        super().__init__(db_session, UsageRequestORM)

    async def get_by_litellm_call_id(self, litellm_call_id: str) -> UsageRequestORM | None:
        """Retrieve a usage request by its LiteLLM call ID.

        Args:
            litellm_call_id: The LiteLLM call ID to search for.

        Returns:
            The usage request if found, None otherwise.
        """
        stmt = select(UsageRequestORM).where(UsageRequestORM.litellm_call_id == litellm_call_id)
        return self._session.execute(stmt).scalars().one_or_none()

    async def get_by_request_id(self, request_id: str) -> UsageRequestORM | None:
        """Retrieve a usage request by its alternate request ID.

        Args:
            request_id: The alternate request ID to search for.

        Returns:
            The usage request if found, None otherwise.
        """
        stmt = select(UsageRequestORM).where(UsageRequestORM.request_id == request_id)
        return self._session.execute(stmt).scalars().one_or_none()

    async def create_many(
        self, requests: list[UsageRequestORM]
    ) -> tuple[list[UsageRequestORM], int]:
        """Create multiple usage request records (idempotent).

        If a usage request with the same litellm_call_id already exists,
        it is skipped via ON CONFLICT DO NOTHING. This method is designed
        for bulk ingestion from collectors.

        Args:
            requests: List of usage request entities to create.

        Returns:
            Tuple of (created requests, skipped count). Duplicates are omitted.
        """
        if not requests:
            return [], 0

        # Use PostgreSQL INSERT ... ON CONFLICT DO NOTHING for idempotency
        # SQLite does not support this natively, so fall back to check-and-insert
        dialect_name = self._session.bind.dialect.name if self._session.bind else ""

        if dialect_name == "postgresql":
            return await self._create_many_postgres(requests)
        else:
            return await self._create_many_generic(requests)

    async def _create_many_postgres(
        self, requests: list[UsageRequestORM]
    ) -> tuple[list[UsageRequestORM], int]:
        """Bulk insert with ON CONFLICT DO NOTHING (PostgreSQL only).

        Uses SQLAlchemy column inspection to build the value dict dynamically,
        eliminating fragility from a hard-coded 27-column mapping.
        Returns only the successfully inserted records to match the
        generic check-and-insert semantics.
        """
        call_ids = [r.litellm_call_id for r in requests]
        mapper = inspect(UsageRequestORM)
        insert_stmt = pg_insert(UsageRequestORM).values(
            [{col.name: getattr(r, col.name) for col in mapper.columns} for r in requests]
        )
        insert_stmt = insert_stmt.on_conflict_do_nothing(index_elements=["litellm_call_id"])

        result = self._session.execute(insert_stmt)
        skipped = len(requests) - result.rowcount  # type: ignore[attr-defined]

        # Query back inserted rows so callers receive only persisted records
        if result.rowcount:  # type: ignore[attr-defined]
            stmt = select(UsageRequestORM).where(UsageRequestORM.litellm_call_id.in_(call_ids))
            created = list(self._session.execute(stmt).scalars().all())
        else:
            created = []

        return created, skipped

    async def _create_many_generic(
        self, requests: list[UsageRequestORM]
    ) -> tuple[list[UsageRequestORM], int]:
        """Fallback check-and-insert for SQLite and other dialects.

        Uses a per-item savepoint (begin_nested) to catch IntegrityError
        without losing the outer transaction state, avoiding TOCTOU races.
        """
        created: list[UsageRequestORM] = []
        skipped = 0

        for request in requests:
            nested = self._session.begin_nested()
            try:
                self._session.add(request)
                self._session.flush()
                created.append(request)
                nested.commit()
            except IntegrityError:
                nested.rollback()
                skipped += 1

        return created, skipped

    async def list_by_key_alias(
        self,
        key_alias: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequestORM]:
        """List usage requests by key alias, ordered by start time desc.

        Args:
            key_alias: The key alias to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching usage requests.
        """
        stmt = (
            select(UsageRequestORM)
            .where(UsageRequestORM.key_alias == key_alias)
            .order_by(UsageRequestORM.started_at.desc().nulls_last())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    async def list_by_litellm_key_id(
        self,
        litellm_key_id: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequestORM]:
        """List usage requests by LiteLLM key ID.

        Args:
            litellm_key_id: The LiteLLM key ID to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching usage requests.
        """
        stmt = (
            select(UsageRequestORM)
            .where(UsageRequestORM.litellm_key_id == litellm_key_id)
            .order_by(UsageRequestORM.started_at.desc().nulls_last())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    async def list_by_model(
        self,
        model: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequestORM]:
        """List usage requests by resolved model.

        Args:
            model: The resolved model to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching usage requests.
        """
        stmt = (
            select(UsageRequestORM)
            .where(UsageRequestORM.resolved_model == model)
            .order_by(UsageRequestORM.started_at.desc().nulls_last())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    async def list_by_provider(
        self,
        provider: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequestORM]:
        """List usage requests by provider.

        Args:
            provider: The provider slug to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching usage requests.
        """
        stmt = (
            select(UsageRequestORM)
            .where(UsageRequestORM.provider == provider)
            .order_by(UsageRequestORM.started_at.desc().nulls_last())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    async def list_by_benchmark_session(
        self,
        benchmark_session_id: UUID,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequestORM]:
        """List usage requests linked to a benchmark session.

        Args:
            benchmark_session_id: The benchmark session UUID.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching usage requests.
        """
        stmt = (
            select(UsageRequestORM)
            .where(UsageRequestORM.benchmark_session_id == benchmark_session_id)
            .order_by(UsageRequestORM.started_at.desc().nulls_last())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    async def list_by_time_range(
        self,
        start: datetime,
        end: datetime,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequestORM]:
        """List usage requests within a time range.

        Args:
            start: Start of time range (datetime).
            end: End of time range (datetime).
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of usage requests in the time range.
        """
        stmt = (
            select(UsageRequestORM)
            .where(
                UsageRequestORM.started_at >= start,
                UsageRequestORM.started_at <= end,
            )
            .order_by(UsageRequestORM.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    async def list_by_status(
        self,
        status: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequestORM]:
        """List usage requests by status.

        Args:
            status: The status to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching usage requests.
        """
        stmt = (
            select(UsageRequestORM)
            .where(UsageRequestORM.status == status)
            .order_by(UsageRequestORM.started_at.desc().nulls_last())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    async def list_by_error_code(
        self,
        error_code: str,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[UsageRequestORM]:
        """List usage requests by error code.

        Args:
            error_code: The error code to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching usage requests.
        """
        stmt = (
            select(UsageRequestORM)
            .where(UsageRequestORM.error_code == error_code)
            .order_by(UsageRequestORM.started_at.desc().nulls_last())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    async def count_by_key_alias(self, key_alias: str) -> int:
        """Count total usage requests for a key alias.

        Args:
            key_alias: The key alias.

        Returns:
            Number of matching usage requests.
        """
        stmt = (
            select(func.count())
            .select_from(UsageRequestORM)
            .where(UsageRequestORM.key_alias == key_alias)
        )
        return self._session.execute(stmt).scalar() or 0

    async def count_by_model(self, model: str) -> int:
        """Count total usage requests for a model.

        Args:
            model: The resolved model.

        Returns:
            Number of matching usage requests.
        """
        stmt = (
            select(func.count())
            .select_from(UsageRequestORM)
            .where(UsageRequestORM.resolved_model == model)
        )
        return self._session.execute(stmt).scalar() or 0

    async def delete_by_benchmark_session(self, benchmark_session_id: UUID) -> int:
        """Delete all usage requests linked to a benchmark session.

        Args:
            benchmark_session_id: The benchmark session UUID.

        Returns:
            Number of usage requests deleted.
        """
        stmt = delete(UsageRequestORM).where(
            UsageRequestORM.benchmark_session_id == benchmark_session_id
        )
        result = cast(CursorResult, self._session.execute(stmt))
        self._session.flush()
        return result.rowcount
