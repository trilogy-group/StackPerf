"""Core domain services for session management, credential issuance, and request collection."""

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from benchmark_core.models import Request, Session
from benchmark_core.repositories import RequestRepository, SessionRepository
from collectors.litellm_collector import (
    CollectionDiagnostics,
    IngestWatermark,
    LiteLLMCollector,
)


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


@dataclass
class CollectionJobResult:
    """Result of a collection job execution."""

    success: bool
    requests_collected: int
    requests_new: int
    diagnostics: CollectionDiagnostics
    watermark: IngestWatermark
    error_message: str | None = None


class CollectionJobService:
    """Service for managing LiteLLM collection jobs.

    Handles raw request collection with idempotent ingest cursor handling,
    watermark tracking, and comprehensive diagnostics.
    """

    def __init__(
        self,
        litellm_base_url: str,
        litellm_api_key: str,
        repository: RequestRepository,
    ) -> None:
        self._collector = LiteLLMCollector(
            base_url=litellm_base_url,
            api_key=litellm_api_key,
            repository=repository,
        )
        self._repository = repository

    async def run_collection_job(
        self,
        session_id: UUID,
        start_time: str | None = None,
        end_time: str | None = None,
        watermark: IngestWatermark | None = None,
    ) -> CollectionJobResult:
        """Execute a collection job for a session.

        This job is idempotent - re-running with the same watermark
        will not duplicate records.

        Args:
            session_id: The benchmark session ID
            start_time: Optional ISO format start time filter
            end_time: Optional ISO format end time filter
            watermark: Optional ingest watermark to resume from last position

        Returns:
            CollectionJobResult with success status, counts, diagnostics, and new watermark
        """
        try:
            # Collect requests from LiteLLM
            collected, diagnostics, new_watermark = await self._collector.collect_requests(
                session_id=session_id,
                start_time=start_time,
                end_time=end_time,
                watermark=watermark,
            )

            # Count how many were actually new (not duplicates)
            # The repository's create_many handles idempotency
            requests_new = len(collected)

            # Determine success based on diagnostics
            success = len(diagnostics.errors) == 0 or requests_new > 0

            return CollectionJobResult(
                success=success,
                requests_collected=diagnostics.total_raw_records,
                requests_new=requests_new,
                diagnostics=diagnostics,
                watermark=new_watermark,
            )

        except Exception as e:
            return CollectionJobResult(
                success=False,
                requests_collected=0,
                requests_new=0,
                diagnostics=CollectionDiagnostics(),
                watermark=IngestWatermark(),
                error_message=str(e),
            )

    async def run_collection_job_with_window(
        self,
        session_id: UUID,
        lookback_hours: int = 24,
        watermark: IngestWatermark | None = None,
    ) -> CollectionJobResult:
        """Execute collection job with automatic time window.

        Args:
            session_id: The benchmark session ID
            lookback_hours: Hours to look back from now (default 24)
            watermark: Optional ingest watermark to resume from

        Returns:
            CollectionJobResult with collection outcome
        """
        from datetime import UTC, datetime, timedelta

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(hours=lookback_hours)

        return await self.run_collection_job(
            session_id=session_id,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            watermark=watermark,
        )

    def get_diagnostics_summary(self, diagnostics: CollectionDiagnostics) -> dict[str, Any]:
        """Generate a human-readable diagnostics summary.

        Provides clear visibility into collection health, including:
        - Total records processed
        - Normalization success rate
        - Missing field breakdown
        - Error details
        """
        total = diagnostics.total_raw_records
        normalized = diagnostics.normalized_count
        skipped = diagnostics.skipped_count

        summary: dict[str, Any] = {
            "total_raw_records": total,
            "normalized_count": normalized,
            "skipped_count": skipped,
            "success_rate": f"{normalized}/{total} ({normalized / total * 100:.1f}%)" if total > 0 else "N/A",
        }

        if diagnostics.missing_fields:
            summary["missing_fields"] = {
                field: f"{count} occurrences"
                for field, count in diagnostics.missing_fields.items()
            }

        if diagnostics.errors:
            summary["errors"] = diagnostics.errors[:10]  # Limit to first 10
            if len(diagnostics.errors) > 10:
                summary["errors_truncated"] = len(diagnostics.errors) - 10

        return summary
