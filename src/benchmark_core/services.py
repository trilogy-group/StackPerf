"""Core domain services for session management and credential issuance."""

from uuid import UUID

from benchmark_core.models import Session
from benchmark_core.repositories import SessionRepository


class SessionService:
    """Service for managing benchmark session lifecycle."""

    def __init__(self, repository: SessionRepository) -> None:
        self._repository = repository

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
    ) -> Session:
        """Create a new benchmark session record."""
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
        return await self._repository.create(session)

    async def get_session(self, session_id: UUID) -> Session | None:
        """Retrieve a session by ID."""
        return await self._repository.get_by_id(session_id)

    async def finalize_session(self, session_id: UUID) -> Session | None:
        """Finalize a session with end time and summary rollups."""
        from datetime import UTC, datetime

        session = await self._repository.get_by_id(session_id)
        if session is None:
            return None

        updated = session.model_copy(update={"ended_at": datetime.now(UTC), "status": "completed"})
        return await self._repository.update(updated)


class CredentialService:
    """Service for issuing session-scoped proxy credentials."""

    async def issue_credential(
        self,
        session_id: UUID,
        experiment_id: str,
        variant_id: str,
        harness_profile: str,
    ) -> str:
        """Issue a short-lived, session-scoped proxy credential.

        The credential encodes session metadata for correlation.
        """
        # Placeholder: actual implementation will integrate with LiteLLM API
        return f"sk-benchmark-{session_id}-{experiment_id[:8]}"

    def render_env_snippet(
        self,
        credential: str,
        proxy_base_url: str,
        model: str,
        harness_profile: str,
    ) -> dict[str, str]:
        """Render environment variable snippet for a harness."""
        return {
            "OPENAI_API_BASE": proxy_base_url,
            "OPENAI_API_KEY": credential,
            "OPENAI_MODEL": model,
        }
