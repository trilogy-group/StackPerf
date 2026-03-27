"""Abstract service definitions for the benchmark core.

Note: The concrete implementations have been moved to the services/ package.
This file is kept for backward compatibility and will be deprecated.
"""

from typing import Any
from uuid import UUID

from benchmark_core.models import Artifact
from benchmark_core.repositories import ArtifactRepository


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
