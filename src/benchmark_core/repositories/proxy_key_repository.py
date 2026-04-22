"""Repository for ProxyKey registry entries."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import ProxyKey as ProxyKeyORM
from benchmark_core.models import ProxyKeyStatus
from benchmark_core.repositories.base import SQLAlchemyRepository


class SQLProxyKeyRepository(SQLAlchemyRepository[ProxyKeyORM]):
    """SQLAlchemy repository for ProxyKey registry entries.

    Provides CRUD operations and lookup helpers for LiteLLM virtual key metadata.
    No API key secrets are ever stored or retrieved.
    """

    def __init__(self, db_session: SQLAlchemySession) -> None:
        """Initialize the repository.

        Args:
            db_session: SQLAlchemy session for database operations.
        """
        super().__init__(db_session, ProxyKeyORM)

    async def get_by_alias(self, key_alias: str) -> ProxyKeyORM | None:
        """Retrieve a proxy key by its alias.

        Args:
            key_alias: The unique key alias.

        Returns:
            The proxy key if found, None otherwise.
        """
        stmt = select(ProxyKeyORM).where(ProxyKeyORM.key_alias == key_alias)
        return self._session.execute(stmt).scalars().one_or_none()

    async def get_by_litellm_key_id(self, litellm_key_id: str) -> ProxyKeyORM | None:
        """Retrieve a proxy key by LiteLLM key ID.

        Args:
            litellm_key_id: The LiteLLM internal key ID.

        Returns:
            The proxy key if found, None otherwise.
        """
        stmt = select(ProxyKeyORM).where(ProxyKeyORM.litellm_key_id == litellm_key_id)
        return self._session.execute(stmt).scalars().first()

    async def list_by_owner(
        self, owner: str, limit: int = 100, offset: int = 0
    ) -> list[ProxyKeyORM]:
        """List proxy keys by owner.

        Args:
            owner: The owner label to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching proxy keys.
        """
        stmt = (
            select(ProxyKeyORM)
            .where(ProxyKeyORM.owner == owner)
            .order_by(ProxyKeyORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    async def list_by_team(self, team: str, limit: int = 100, offset: int = 0) -> list[ProxyKeyORM]:
        """List proxy keys by team.

        Args:
            team: The team label to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching proxy keys.
        """
        stmt = (
            select(ProxyKeyORM)
            .where(ProxyKeyORM.team == team)
            .order_by(ProxyKeyORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    async def list_by_customer(
        self, customer: str, limit: int = 100, offset: int = 0
    ) -> list[ProxyKeyORM]:
        """List proxy keys by customer.

        Args:
            customer: The customer label to filter by.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching proxy keys.
        """
        stmt = (
            select(ProxyKeyORM)
            .where(ProxyKeyORM.customer == customer)
            .order_by(ProxyKeyORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    async def list_active(self, limit: int = 100, offset: int = 0) -> list[ProxyKeyORM]:
        """List active proxy keys.

        Args:
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of active proxy keys.
        """
        stmt = (
            select(ProxyKeyORM)
            .where(ProxyKeyORM.status == ProxyKeyStatus.ACTIVE)
            .order_by(ProxyKeyORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())

    async def revoke(self, proxy_key_id: UUID) -> ProxyKeyORM | None:
        """Mark a proxy key as revoked.

        Args:
            proxy_key_id: The UUID of the proxy key to revoke.

        Returns:
            The revoked proxy key, or None if not found.
            Returns the key unchanged if already revoked or expired.
        """
        proxy_key = await self.get_by_id(proxy_key_id)
        if proxy_key is None:
            return None

        if proxy_key.status in (ProxyKeyStatus.REVOKED, ProxyKeyStatus.EXPIRED):
            return proxy_key

        proxy_key.status = ProxyKeyStatus.REVOKED
        proxy_key.revoked_at = datetime.now(UTC)
        proxy_key.updated_at = datetime.now(UTC)
        self._session.flush()
        return proxy_key

    async def list_by_proxy_credential_id(
        self, proxy_credential_id: UUID, limit: int = 100, offset: int = 0
    ) -> list[ProxyKeyORM]:
        """List proxy keys linked to a session-scoped proxy credential.

        Args:
            proxy_credential_id: The proxy credential UUID.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of matching proxy keys.
        """
        stmt = (
            select(ProxyKeyORM)
            .where(ProxyKeyORM.proxy_credential_id == proxy_credential_id)
            .order_by(ProxyKeyORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self._session.execute(stmt).scalars().all())
