"""Abstract service definitions for the benchmark core.

Note: Concrete implementations have been moved to the services/ package.
This file is kept for backward compatibility and will be deprecated.
"""

from datetime import UTC, datetime
from uuid import UUID

from benchmark_core.models import ProxyCredential, Session
from benchmark_core.repositories import ProxyCredentialRepository, SessionRepository

# Re-export CredentialService so existing callers don't break.
from benchmark_core.services.credential_service import (  # noqa: F401
    CredentialService,
)


class SessionService:
    """Service for managing benchmark session lifecycle.

    Coordinates session creation with credential issuance to ensure
    every session has a unique proxy credential before harness launch.
    """

    def __init__(
        self,
        session_repository: SessionRepository,
        credential_repository: ProxyCredentialRepository | None = None,
        credential_service: "CredentialService | None" = None,
    ) -> None:
        """Initialize the session service.

        Args:
            session_repository: Repository for session persistence
            credential_repository: Repository for credential metadata persistence
            credential_service: Service for issuing LiteLLM credentials
        """
        self._session_repo = session_repository
        self._credential_repo = credential_repository
        self._credential_service = credential_service

    async def create_session(
        self,
        experiment_id: str,
        variant_id: str,
        task_card_id: str,
        harness_profile: str,
        repo_path: str,
        git_branch: str,
        git_commit: str,
        git_dirty: bool = False,
        operator_label: str | None = None,
        issue_credential: bool = True,
    ) -> tuple[Session, ProxyCredential | None]:
        """Create a new benchmark session with optional credential issuance.

        When issue_credential=True (default), this method:
        1. Creates a session record
        2. Issues a session-scoped proxy credential
        3. Persists credential metadata to the benchmark database
        4. Updates the session with the credential reference

        Args:
            experiment_id: Experiment identifier
            variant_id: Variant identifier
            task_card_id: Task card identifier
            harness_profile: Harness profile name
            repo_path: Absolute repository root path
            git_branch: Active git branch
            git_commit: Commit SHA
            git_dirty: Whether the working tree is dirty
            operator_label: Optional operator-provided label
            issue_credential: Whether to issue a proxy credential

        Returns:
            Tuple of (Session, ProxyCredential | None)

        Raises:
            RuntimeError: If credential issuance is requested but
                credential_repository or credential_service is not configured.
        """
        # Create session record first
        session = Session(
            experiment_id=experiment_id,
            variant_id=variant_id,
            task_card_id=task_card_id,
            harness_profile=harness_profile,
            repo_path=repo_path,
            git_branch=git_branch,
            git_commit=git_commit,
            git_dirty=git_dirty,
            operator_label=operator_label,
        )
        session = await self._session_repo.create(session)

        credential: ProxyCredential | None = None

        # Issue and persist credential if requested
        if issue_credential:
            if self._credential_service is None or self._credential_repo is None:
                raise RuntimeError(
                    "Credential issuance requested but credential_service "
                    "and credential_repository must be configured"
                )

            try:
                # Issue the credential
                credential = await self._credential_service.issue_credential(
                    session_id=session.session_id,
                    experiment_id=experiment_id,
                    variant_id=variant_id,
                    harness_profile=harness_profile,
                )

                # Persist credential metadata (without the secret)
                await self._credential_repo.create(credential)

                # Update session with credential reference
                session = session.model_copy(
                    update={"proxy_credential_alias": credential.key_alias}
                )
                session = await self._session_repo.update(session)
            except Exception:
                # Re-raise the exception to propagate the error
                # The transaction will be rolled back by the database session manager
                # at a higher level, preventing orphaned sessions without credentials
                raise

        return session, credential

    async def get_session(self, session_id: UUID) -> Session | None:
        """Retrieve a session by ID."""
        return await self._session_repo.get_by_id(session_id)

    async def get_session_with_credential(
        self, session_id: UUID
    ) -> tuple[Session | None, ProxyCredential | None]:
        """Retrieve a session and its associated credential metadata.

        Args:
            session_id: Session UUID to look up

        Returns:
            Tuple of (Session | None, ProxyCredential | None)
        """
        session = await self._session_repo.get_by_id(session_id)
        if session is None or self._credential_repo is None:
            return session, None

        credential = await self._credential_repo.get_by_session(session_id)
        return session, credential

    async def finalize_session(self, session_id: UUID) -> Session | None:
        """Finalize a session with end time and summary rollups.

        Also revokes the session's proxy credential if present.
        """
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            return None

        # Revoke credential if present and repository available
        if session.proxy_credential_alias and self._credential_repo:
            await self._credential_repo.revoke(session_id)

        updated = session.model_copy(update={"ended_at": datetime.now(UTC), "status": "completed"})
        return await self._session_repo.update(updated)
