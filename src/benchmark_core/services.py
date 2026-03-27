"""Core domain services for session management and credential issuance."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from benchmark_core.models import ProxyCredential, Session
from benchmark_core.repositories import ProxyCredentialRepository, SessionRepository


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
            session = session.model_copy(update={"proxy_credential_alias": credential.key_alias})
            session = await self._session_repo.update(session)

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
        if session.proxy_credential_id and self._credential_repo:
            await self._credential_repo.revoke(session_id)

        updated = session.model_copy(update={"ended_at": datetime.now(UTC), "status": "completed"})
        return await self._session_repo.update(updated)


class CredentialService:
    """Service for issuing and managing session-scoped proxy credentials.

    Implements the key aliasing convention and metadata tagging strategy
    for correlating LiteLLM traffic back to benchmark sessions.
    """

    def __init__(
        self,
        litellm_base_url: str = "http://localhost:4000",
        master_key: str | None = None,
    ) -> None:
        """Initialize the credential service.

        Args:
            litellm_base_url: Base URL for LiteLLM proxy API
            master_key: LiteLLM master key for API authentication
        """
        self.litellm_base_url = litellm_base_url.rstrip("/")
        self.master_key = master_key

    def _generate_key_alias(
        self,
        session_id: UUID,
        experiment_id: str,
        variant_id: str,
    ) -> str:
        """Generate a stable key alias for correlation.

        Format: session-{session_id[:8]}-{experiment_id[:8]}-{variant_id[:8]}

        This alias is:
        - Human-readable for operators
        - Unique per session
        - Joinable back to session via metadata
        """
        session_short = str(session_id)[:8]
        exp_short = experiment_id[:8] if len(experiment_id) >= 8 else experiment_id
        var_short = variant_id[:8] if len(variant_id) >= 8 else variant_id
        return f"session-{session_short}-{exp_short}-{var_short}"

    def _build_metadata_tags(
        self,
        session_id: UUID,
        experiment_id: str,
        variant_id: str,
        harness_profile: str,
    ) -> dict[str, str]:
        """Build metadata tags for LiteLLM credential.

        These tags enable joining LiteLLM request logs back to
        the benchmark session and its dimensions.
        """
        return {
            "benchmark_session_id": str(session_id),
            "benchmark_experiment_id": experiment_id,
            "benchmark_variant_id": variant_id,
            "benchmark_harness_profile": harness_profile,
            "benchmark_source": "opensymphony",
        }

    def _generate_api_key(self, alias: str) -> str:
        """Generate a unique API key for the credential.

        Creates a cryptographically random key prefixed with
        the alias for identification.
        """
        import secrets

        random_suffix = secrets.token_urlsafe(32)
        return f"sk-bm-{alias}-{random_suffix}"

    async def issue_credential(
        self,
        session_id: UUID,
        experiment_id: str,
        variant_id: str,
        harness_profile: str,
        ttl_hours: int = 24,
    ) -> ProxyCredential:
        """Issue a session-scoped proxy credential.

        Creates a LiteLLM virtual key with:
        - Unique key alias for correlation
        - Metadata tags linking to session
        - Configurable TTL (default 24 hours)

        Args:
            session_id: Benchmark session UUID
            experiment_id: Experiment identifier
            variant_id: Variant identifier
            harness_profile: Harness profile name
            ttl_hours: Credential time-to-live in hours

        Returns:
            ProxyCredential with metadata and API key

        Note:
            This creates an in-memory credential. To persist
            metadata to the benchmark database, use
            ProxyCredentialRepository.create().
        """
        # Generate stable alias for correlation
        key_alias = self._generate_key_alias(session_id, experiment_id, variant_id)

        # Build metadata tags for LiteLLM correlation
        metadata_tags = self._build_metadata_tags(
            session_id, experiment_id, variant_id, harness_profile
        )

        # Generate unique API key
        api_key = self._generate_api_key(key_alias)

        # Calculate expiration
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

        # Create credential domain model
        credential = ProxyCredential(
            session_id=session_id,
            key_alias=key_alias,
            api_key=api_key,  # type: ignore[arg-type]
            experiment_id=experiment_id,
            variant_id=variant_id,
            harness_profile=harness_profile,
            metadata_tags=metadata_tags,
            expires_at=expires_at,
            is_active=True,
        )

        return credential

    async def revoke_credential(self, credential: ProxyCredential) -> ProxyCredential:
        """Revoke an active credential.

        Marks the credential as revoked and records revocation time.
        Note: Actual LiteLLM key revocation requires separate API call.

        Args:
            credential: Credential to revoke

        Returns:
            Updated credential with is_active=False
        """
        from pydantic import SecretStr

        updated = credential.model_copy(
            update={
                "is_active": False,
                "revoked_at": datetime.now(UTC),
                # Clear the secret from memory
                "api_key": SecretStr("REDACTED"),
            }
        )
        return updated

    def render_env_snippet(
        self,
        credential: ProxyCredential,
        proxy_base_url: str,
        model: str,
    ) -> dict[str, str]:
        """Render environment variable snippet for a harness.

        Args:
            credential: Proxy credential with API key
            proxy_base_url: LiteLLM proxy base URL
            model: Model identifier/alias

        Returns:
            Dictionary of environment variables
        """
        return {
            "OPENAI_API_BASE": proxy_base_url,
            "OPENAI_API_KEY": credential.api_key.get_secret_value(),
            "OPENAI_MODEL": model,
            "LITELLM_SESSION_ALIAS": credential.key_alias,
        }

    def render_env_shell(self, env_vars: dict[str, str]) -> str:
        """Render environment variables as shell export commands.

        Args:
            env_vars: Dictionary of environment variables

        Returns:
            Shell commands for setting environment
        """
        lines = []
        for key, value in env_vars.items():
            # Quote the value for shell safety
            escaped = value.replace("'", "'\\''")
            lines.append(f"export {key}='{escaped}'")
        return "\n".join(lines)

    def render_env_dotenv(self, env_vars: dict[str, str]) -> str:
        """Render environment variables as dotenv format.

        Args:
            env_vars: Dictionary of environment variables

        Returns:
            Dotenv file content
        """
        lines = []
        for key, value in env_vars.items():
            # Escape special characters for dotenv
            if " " in value or "#" in value or "'" in value or '"' in value:
                escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{key}="{escaped}"')
            else:
                lines.append(f"{key}={value}")
        return "\n".join(lines)
