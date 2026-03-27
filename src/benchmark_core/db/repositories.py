"""SQLAlchemy repository implementations for session, request, and credential storage."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session as SQLAlchemySession

from benchmark_core.db.models import (
    Experiment,
    TaskCard,
    Variant,
)
from benchmark_core.db.models import (
    ProxyCredential as ProxyCredentialORM,
)
from benchmark_core.db.models import (
    Request as DBRequest,
)
from benchmark_core.db.models import (
    Session as DBSession,
)
from benchmark_core.models import ProxyCredential, Request, Session
from benchmark_core.repositories import (
    ProxyCredentialRepository as AbstractProxyCredentialRepository,
)
from benchmark_core.repositories import (
    RequestRepository,
    SessionRepository,
)
from benchmark_core.repositories.base import (
    DuplicateIdentifierError,
    ReferentialIntegrityError,
)


class SQLAlchemySessionRepository(SessionRepository):
    """SQLAlchemy implementation of SessionRepository."""

    def __init__(self, db_session: SQLAlchemySession) -> None:
        self._session = db_session

    async def create(self, session: Session) -> Session:
        """Create a new session record in the database."""
        db_session = DBSession(
            id=session.session_id,
            experiment_id=UUID(session.experiment_id)
            if isinstance(session.experiment_id, str)
            else session.experiment_id,
            variant_id=UUID(session.variant_id)
            if isinstance(session.variant_id, str)
            else session.variant_id,
            task_card_id=UUID(session.task_card_id)
            if isinstance(session.task_card_id, str)
            else session.task_card_id,
            harness_profile=session.harness_profile,
            repo_path=session.repo_path,
            git_branch=session.git_branch,
            git_commit=session.git_commit,
            git_dirty=session.git_dirty,
            operator_label=session.operator_label,
            proxy_credential_alias=session.proxy_credential_alias,
            started_at=session.started_at,
            ended_at=session.ended_at,
            status=session.status,
        )
        self._session.add(db_session)
        self._session.flush()
        return session

    async def get_by_id(self, session_id: UUID) -> Session | None:
        """Retrieve a session by ID."""
        db_session = self._session.query(DBSession).filter_by(id=session_id).first()
        if db_session is None:
            return None
        return self._to_domain(db_session)

    async def update(self, session: Session) -> Session:
        """Update an existing session."""
        db_session = self._session.query(DBSession).filter_by(id=session.session_id).first()
        if db_session is None:
            raise ValueError(f"Session {session.session_id} not found")

        db_session.status = session.status
        db_session.ended_at = session.ended_at
        db_session.proxy_credential_alias = session.proxy_credential_alias
        db_session.operator_label = session.operator_label
        self._session.flush()
        return session

    async def list_by_experiment(self, experiment_id: str) -> list[Session]:
        """List all sessions for an experiment."""
        exp_uuid = UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id
        db_sessions = self._session.query(DBSession).filter_by(experiment_id=exp_uuid).all()
        return [self._to_domain(s) for s in db_sessions]

    def _to_domain(self, db_session: DBSession) -> Session:
        """Convert DB model to domain model."""
        return Session(
            session_id=db_session.id,
            experiment_id=str(db_session.experiment_id),
            variant_id=str(db_session.variant_id),
            task_card_id=str(db_session.task_card_id),
            harness_profile=db_session.harness_profile,
            repo_path=db_session.repo_path,
            git_branch=db_session.git_branch,
            git_commit=db_session.git_commit,
            git_dirty=db_session.git_dirty,
            operator_label=db_session.operator_label,
            proxy_credential_alias=db_session.proxy_credential_alias,
            started_at=db_session.started_at,
            ended_at=db_session.ended_at,
            status=db_session.status,
        )

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
    ) -> DBSession:
        """Safely create a session with validation and duplicate rejection.

        Args:
            experiment_id: The experiment UUID.
            variant_id: The variant UUID.
            task_card_id: The task card UUID.
            harness_profile: The harness profile name.
            repo_path: Absolute path to the repository.
            git_branch: Active git branch.
            git_commit: Commit SHA.
            git_dirty: Whether the working tree is dirty.
            operator_label: Optional operator-provided label.
            proxy_credential_alias: Optional proxy credential key alias.

        Returns:
            The created session.

        Raises:
            DuplicateIdentifierError: If a session with the same operator_label exists.
            ReferentialIntegrityError: If any referenced entity does not exist.
        """
        # Check for duplicate operator_label if provided
        if operator_label:
            existing = (
                self._session.query(DBSession).filter_by(operator_label=operator_label).first()
            )
            if existing:
                raise DuplicateIdentifierError(
                    f"Session with identifier '{operator_label}' already exists"
                )

        # Verify referential integrity
        # Convert UUIDs to ensure proper type handling
        exp_id = experiment_id if isinstance(experiment_id, UUID) else UUID(experiment_id)
        var_id = variant_id if isinstance(variant_id, UUID) else UUID(variant_id)
        task_id = task_card_id if isinstance(task_card_id, UUID) else UUID(task_card_id)

        experiment = self._session.get(Experiment, exp_id)
        if experiment is None:
            raise ReferentialIntegrityError(f"Experiment '{experiment_id}' does not exist")

        variant = self._session.get(Variant, var_id)
        if variant is None:
            raise ReferentialIntegrityError(f"Variant '{variant_id}' does not exist")

        task_card = self._session.get(TaskCard, task_id)
        if task_card is None:
            raise ReferentialIntegrityError(f"TaskCard '{task_card_id}' does not exist")

        # Create the session with proper UUID types
        session = DBSession(
            id=uuid4(),
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
            started_at=datetime.now(UTC),
            status="active",
        )
        self._session.add(session)
        self._session.flush()
        return session

    async def finalize_session(
        self,
        session_id: UUID,
        status: str = "completed",
        ended_at: datetime | None = None,
    ) -> DBSession | None:
        """Finalize a session with end time and status.

        Args:
            session_id: UUID of the session to finalize.
            status: Final status (completed, failed, cancelled).
            ended_at: Optional end timestamp. Defaults to current UTC time.

        Returns:
            The updated session, or None if not found.
        """
        db_session = self._session.query(DBSession).filter_by(id=session_id).first()
        if db_session is None:
            return None

        if ended_at is None:
            ended_at = datetime.now(UTC)

        db_session.ended_at = ended_at
        db_session.status = status
        self._session.flush()
        return db_session


class SQLAlchemyRequestRepository(RequestRepository):
    """SQLAlchemy implementation of RequestRepository."""

    def __init__(self, db_session: SQLAlchemySession) -> None:
        self._session = db_session

    async def create(self, request: Request) -> Request:
        """Create a new request record in the database."""
        db_request = DBRequest(
            request_id=request.request_id,
            session_id=request.session_id,
            provider=request.provider,
            model=request.model,
            timestamp=request.timestamp,
            latency_ms=request.latency_ms,
            ttft_ms=request.ttft_ms,
            tokens_prompt=request.tokens_prompt,
            tokens_completion=request.tokens_completion,
            error=request.error,
            error_message=request.error_message,
            cache_hit=request.cache_hit,
            request_metadata=request.metadata,
        )
        self._session.add(db_request)
        self._session.flush()
        return request

    async def create_many(self, requests: list[Request]) -> list[Request]:
        """Create multiple request records in the database."""
        db_requests = [
            DBRequest(
                request_id=r.request_id,
                session_id=r.session_id,
                provider=r.provider,
                model=r.model,
                timestamp=r.timestamp,
                latency_ms=r.latency_ms,
                ttft_ms=r.ttft_ms,
                tokens_prompt=r.tokens_prompt,
                tokens_completion=r.tokens_completion,
                error=r.error,
                error_message=r.error_message,
                cache_hit=r.cache_hit,
                request_metadata=r.metadata,
            )
            for r in requests
        ]
        self._session.add_all(db_requests)
        self._session.flush()
        return requests

    async def get_by_session(self, session_id: UUID) -> list[Request]:
        """Get all requests for a session from the database."""
        db_requests = self._session.query(DBRequest).filter_by(session_id=session_id).all()

        return [
            Request(
                request_id=r.request_id,
                session_id=r.session_id,
                provider=r.provider,
                model=r.model,
                timestamp=r.timestamp,
                latency_ms=r.latency_ms,
                ttft_ms=r.ttft_ms,
                tokens_prompt=r.tokens_prompt,
                tokens_completion=r.tokens_completion,
                error=r.error,
                error_message=r.error_message,
                cache_hit=r.cache_hit,
                metadata=r.request_metadata,
            )
            for r in db_requests
        ]

    async def get_by_request_id(self, request_id: str) -> Request | None:
        """Get a request by its LiteLLM request ID from the database."""
        db_request = self._session.query(DBRequest).filter_by(request_id=request_id).first()
        if db_request is None:
            return None

        return Request(
            request_id=db_request.request_id,
            session_id=db_request.session_id,
            provider=db_request.provider,
            model=db_request.model,
            timestamp=db_request.timestamp,
            latency_ms=db_request.latency_ms,
            ttft_ms=db_request.ttft_ms,
            tokens_prompt=db_request.tokens_prompt,
            tokens_completion=db_request.tokens_completion,
            error=db_request.error,
            error_message=db_request.error_message,
            cache_hit=db_request.cache_hit,
            metadata=db_request.request_metadata,
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
