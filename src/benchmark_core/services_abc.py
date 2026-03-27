"""Core domain services for session management and credential issuance."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from benchmark_core.models import Artifact, Session, SessionOutcomeState
from benchmark_core.repositories import ArtifactRepository, SessionRepository


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
        notes: str | None = None,
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
            notes=notes,
        )
        return await self._repository.create(session)

    async def get_session(self, session_id: UUID) -> Session | None:
        """Retrieve a session by ID."""
        return await self._repository.get_by_id(session_id)

    async def update_session_notes(self, session_id: UUID, notes: str | None) -> Session | None:
        """Update session notes."""
        session = await self._repository.get_by_id(session_id)
        if session is None:
            return None

        updated = session.model_copy(update={"notes": notes})
        return await self._repository.update(updated)

    async def finalize_session(
        self,
        session_id: UUID,
        outcome_state: SessionOutcomeState | None = None,
    ) -> Session | None:
        """Finalize a session with end time, summary rollups, and outcome state.

        Args:
            session_id: The session ID to finalize
            outcome_state: The outcome state (valid, invalid, or aborted).
                          Defaults to VALID if not specified.
        """
        session = await self._repository.get_by_id(session_id)
        if session is None:
            return None

        # Default to VALID outcome if not specified
        final_outcome = outcome_state.value if outcome_state else SessionOutcomeState.VALID.value

        updated = session.model_copy(
            update={
                "ended_at": datetime.now(UTC),
                "status": "completed",
                "outcome_state": final_outcome,
            }
        )
        return await self._repository.update(updated)


class CredentialService:
    """Service for rendering and managing session-scoped proxy credentials."""

    async def issue_credential(
        self,
        session_id: UUID,
        experiment_id: str,
        variant_id: str,
        harness_profile: str,
    ) -> str:
        """Generate a session-scoped proxy credential.

        Currently returns a placeholder credential. The actual implementation
        will integrate with LiteLLM API for short-lived credential issuance.

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


class ArtifactRegistryService:
    """Service for registering and managing benchmark artifacts."""

    def __init__(self, repository: ArtifactRepository) -> None:
        self._repository = repository

    async def register_artifact(
        self,
        artifact_type: str,
        name: str,
        content_type: str,
        storage_path: str,
        session_id: UUID | None = None,
        experiment_id: UUID | None = None,
        size_bytes: int | None = None,
        artifact_metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        """Register a new artifact.

        Args:
            artifact_type: Type of artifact (e.g., "export", "report", "bundle")
            name: Artifact name
            content_type: MIME content type
            storage_path: Path to stored artifact
            session_id: Associated session ID (for session-scoped artifacts)
            experiment_id: Associated experiment ID (for experiment-scoped artifacts)
            size_bytes: Size in bytes
            artifact_metadata: Additional metadata

        Raises:
            ValueError: If neither session_id nor experiment_id is provided.
        """
        if session_id is None and experiment_id is None:
            raise ValueError("Either session_id or experiment_id must be provided")

        artifact = Artifact(
            artifact_type=artifact_type,
            name=name,
            content_type=content_type,
            storage_path=storage_path,
            session_id=session_id,
            experiment_id=experiment_id,
            size_bytes=size_bytes,
            artifact_metadata=artifact_metadata or {},
        )
        return await self._repository.create(artifact)

    async def get_artifact(self, artifact_id: UUID) -> Artifact | None:
        """Retrieve an artifact by ID."""
        return await self._repository.get_by_id(artifact_id)

    async def list_session_artifacts(self, session_id: UUID) -> list[Artifact]:
        """List all artifacts for a session."""
        return await self._repository.list_by_session(session_id)

    async def list_experiment_artifacts(self, experiment_id: UUID) -> list[Artifact]:
        """List all artifacts for an experiment."""
        return await self._repository.list_by_experiment(experiment_id)

    async def remove_artifact(self, artifact_id: UUID) -> bool:
        """Remove an artifact from the registry."""
        return await self._repository.delete(artifact_id)
