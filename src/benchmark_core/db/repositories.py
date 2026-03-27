"""SQLAlchemy repository implementations."""

from uuid import UUID

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from benchmark_core.db.models import ProxyCredential as ProxyCredentialORM
from benchmark_core.models import ProxyCredential
from benchmark_core.repositories import (
    ProxyCredentialRepository as AbstractProxyCredentialRepository,
)


class ProxyCredentialRepository(AbstractProxyCredentialRepository):
    """SQLAlchemy implementation of proxy credential metadata repository.

    IMPORTANT: This repository only stores metadata (alias, tags, references).
    The actual API key secrets are NEVER stored in the benchmark database.
    Secrets are managed by LiteLLM and only exist in memory during issuance.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize with database session.

        Args:
            db_session: SQLAlchemy async session
        """
        self._session = db_session

    async def create(self, credential: ProxyCredential) -> ProxyCredential:
        """Persist credential metadata to the database.

        Stores alias, metadata tags, and references for correlation.
        The api_key field is explicitly NOT stored.

        Args:
            credential: Domain model with credential information

        Returns:
            Credential with persisted metadata
        """
        orm_credential = ProxyCredentialORM(
            id=credential.credential_id,
            session_id=credential.session_id,
            key_alias=credential.key_alias,
            # api_key is NOT stored - only in LiteLLM
            experiment_id=credential.experiment_id,
            variant_id=credential.variant_id,
            harness_profile=credential.harness_profile,
            litellm_key_id=credential.litellm_key_id,
            expires_at=credential.expires_at,
            is_active=credential.is_active,
            created_at=credential.created_at,
            revoked_at=credential.revoked_at,
        )

        self._session.add(orm_credential)
        await self._session.flush()

        # Return domain model with metadata (secret is cleared for safety)
        return credential.model_copy(
            update={
                "api_key": SecretStr("[NOT_STORED_IN_DB]"),
            }
        )

    async def get_by_session(self, session_id: UUID) -> ProxyCredential | None:
        """Retrieve credential metadata by session ID.

        Args:
            session_id: Session UUID to look up

        Returns:
            Credential metadata (without secret) or None
        """
        stmt = select(ProxyCredentialORM).where(ProxyCredentialORM.session_id == session_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        return self._to_domain(orm)

    async def get_by_alias(self, key_alias: str) -> ProxyCredential | None:
        """Retrieve credential metadata by key alias.

        Args:
            key_alias: Key alias to look up

        Returns:
            Credential metadata (without secret) or None
        """
        stmt = select(ProxyCredentialORM).where(ProxyCredentialORM.key_alias == key_alias)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        return self._to_domain(orm)

    async def update(self, credential: ProxyCredential) -> ProxyCredential:
        """Update credential metadata.

        Args:
            credential: Credential with updated fields

        Returns:
            Updated credential
        """
        stmt = select(ProxyCredentialORM).where(ProxyCredentialORM.id == credential.credential_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one()

        orm.is_active = credential.is_active
        orm.revoked_at = credential.revoked_at
        orm.litellm_key_id = credential.litellm_key_id

        await self._session.flush()

        return credential

    async def revoke(self, session_id: UUID) -> ProxyCredential | None:
        """Mark a credential as revoked.

        Args:
            session_id: Session ID whose credential should be revoked

        Returns:
            Updated credential metadata or None if not found
        """
        from datetime import UTC, datetime

        stmt = select(ProxyCredentialORM).where(ProxyCredentialORM.session_id == session_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm is None:
            return None

        orm.is_active = False
        orm.revoked_at = datetime.now(UTC)

        await self._session.flush()

        return self._to_domain(orm)

    def _to_domain(self, orm: ProxyCredentialORM) -> ProxyCredential:
        """Convert ORM model to domain model.

        The api_key is always set to a placeholder since secrets
        are never stored in the benchmark database.

        Args:
            orm: SQLAlchemy ORM model

        Returns:
            Domain model with metadata (no secret)
        """
        from datetime import UTC, datetime

        return ProxyCredential(
            credential_id=orm.id,
            session_id=orm.session_id,
            key_alias=orm.key_alias,
            api_key=SecretStr("[STORED_IN_LITELLM_ONLY]"),  # Never stored in DB
            experiment_id=orm.experiment_id,
            variant_id=orm.variant_id,
            harness_profile=orm.harness_profile,
            litellm_key_id=orm.litellm_key_id,
            expires_at=orm.expires_at,
            is_active=orm.is_active,
            created_at=orm.created_at or datetime.now(UTC),
            revoked_at=orm.revoked_at,
        )
