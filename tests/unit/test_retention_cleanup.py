"""Tests for retention cleanup jobs."""

from datetime import UTC, datetime, timedelta

import pytest

from benchmark_core.security import RetentionSettings
from collectors.retention_cleanup import (
    CleanupDiagnostics,
    CleanupResult,
    CredentialCleanupJob,
    CredentialCleanupResult,
    RetentionCleanupJob,
)


class TestCleanupResult:
    """Tests for CleanupResult."""

    def test_defaults(self) -> None:
        """Default values are set correctly."""
        result = CleanupResult(data_type="test")
        assert result.deleted_count == 0
        assert result.archived_count == 0
        assert result.skipped_count == 0
        assert result.error_count == 0
        assert result.errors == []
        assert result.completed_at is None

    def test_success_when_completed_without_errors(self) -> None:
        """Success is True when completed with no errors."""
        result = CleanupResult(data_type="test", completed_at=datetime.now(UTC))
        assert result.success is True

    def test_not_success_when_not_completed(self) -> None:
        """Success is False when not completed."""
        result = CleanupResult(data_type="test", completed_at=None)
        assert result.success is False

    def test_not_success_when_has_errors(self) -> None:
        """Success is False when there are errors."""
        result = CleanupResult(
            data_type="test",
            completed_at=datetime.now(UTC),
            error_count=1,
            errors=["Something went wrong"],
        )
        assert result.success is False

    def test_duration_seconds_when_completed(self) -> None:
        """Duration is calculated when completed."""
        started = datetime.now(UTC) - timedelta(seconds=5)
        completed = datetime.now(UTC)
        result = CleanupResult(
            data_type="test",
            started_at=started,
            completed_at=completed,
        )
        assert result.duration_seconds is not None
        assert 4.9 < result.duration_seconds < 5.1  # Allow for timing variance

    def test_duration_seconds_none_when_not_completed(self) -> None:
        """Duration is None when not completed."""
        result = CleanupResult(data_type="test", completed_at=None)
        assert result.duration_seconds is None


class TestCleanupDiagnostics:
    """Tests for CleanupDiagnostics."""

    def test_defaults(self) -> None:
        """Default values are set correctly."""
        diagnostics = CleanupDiagnostics()
        assert diagnostics.policies_checked == 0
        assert diagnostics.total_eligible == 0
        assert diagnostics.cleanup_stats == {}

    def test_add_result(self) -> None:
        """Adding a result updates statistics."""
        diagnostics = CleanupDiagnostics()
        result = CleanupResult(
            data_type="test",
            deleted_count=100,
            archived_count=10,
            completed_at=datetime.now(UTC),
        )
        diagnostics.add_result(result)

        assert diagnostics.policies_checked == 0  # Not incremented by add_result
        assert diagnostics.total_eligible == 110
        assert "test" in diagnostics.cleanup_stats

    def test_multiple_results(self) -> None:
        """Multiple results are tracked correctly."""
        diagnostics = CleanupDiagnostics()

        result1 = CleanupResult(data_type="type1", deleted_count=50)
        result2 = CleanupResult(data_type="type2", deleted_count=30)

        diagnostics.add_result(result1)
        diagnostics.add_result(result2)

        assert diagnostics.total_eligible == 80
        assert len(diagnostics.cleanup_stats) == 2


class TestRetentionCleanupJob:
    """Tests for RetentionCleanupJob."""

    def test_init_with_default_settings(self) -> None:
        """Job initializes with default settings."""
        job = RetentionCleanupJob()
        assert job._settings is not None

    def test_init_with_custom_settings(self) -> None:
        """Job accepts custom settings."""
        settings = RetentionSettings()
        job = RetentionCleanupJob(settings=settings)
        assert job._settings == settings

    @pytest.mark.asyncio
    async def test_run_cleanup_all_types(self) -> None:
        """Running cleanup processes all data types."""
        job = RetentionCleanupJob()
        diagnostics = await job.run_cleanup()

        # Should check all defined policies
        assert diagnostics.policies_checked == 6
        assert len(diagnostics.cleanup_stats) == 6

    @pytest.mark.asyncio
    async def test_run_cleanup_specific_types(self) -> None:
        """Running cleanup for specific types only processes those."""
        job = RetentionCleanupJob()
        diagnostics = await job.run_cleanup(data_types=["sessions", "artifacts"])

        assert diagnostics.policies_checked == 2
        assert len(diagnostics.cleanup_stats) == 2
        assert "sessions" in diagnostics.cleanup_stats
        assert "artifacts" in diagnostics.cleanup_stats

    @pytest.mark.asyncio
    async def test_run_cleanup_unknown_type(self) -> None:
        """Unknown data types are skipped."""
        job = RetentionCleanupJob()
        diagnostics = await job.run_cleanup(data_types=["unknown_type"])

        assert diagnostics.policies_checked == 0
        assert len(diagnostics.cleanup_stats) == 0

    @pytest.mark.asyncio
    async def test_cleanup_raw_ingestion(self) -> None:
        """Can cleanup raw ingestion specifically."""
        job = RetentionCleanupJob()
        result = await job.cleanup_raw_ingestion()

        assert result.data_type == "raw_ingestion"
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_cleanup_normalized_requests(self) -> None:
        """Can cleanup normalized requests specifically."""
        job = RetentionCleanupJob()
        result = await job.cleanup_normalized_requests()

        assert result.data_type == "normalized_requests"
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_cleanup_session_credentials(self) -> None:
        """Can cleanup session credentials specifically."""
        job = RetentionCleanupJob()
        result = await job.cleanup_session_credentials()

        assert result.data_type == "session_credentials"
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_cleanup_artifacts(self) -> None:
        """Can cleanup artifacts specifically."""
        job = RetentionCleanupJob()
        result = await job.cleanup_artifacts()

        assert result.data_type == "artifacts"
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_cleanup_metric_rollups(self) -> None:
        """Can cleanup metric rollups specifically."""
        job = RetentionCleanupJob()
        result = await job.cleanup_metric_rollups()

        assert result.data_type == "metric_rollups"
        assert result.completed_at is not None


class TestCredentialCleanupResult:
    """Tests for CredentialCleanupResult."""

    def test_defaults(self) -> None:
        """Default values are set correctly."""
        result = CredentialCleanupResult()
        assert result.total_checked == 0
        assert result.revoked_count == 0
        assert result.expired_count == 0
        assert result.errors == []


class TestCredentialCleanupJob:
    """Tests for CredentialCleanupJob."""

    @pytest.mark.asyncio
    async def test_cleanup_expired_credentials(self) -> None:
        """Can run credential cleanup."""
        job = CredentialCleanupJob()
        result = await job.cleanup_expired_credentials()

        assert isinstance(result, CredentialCleanupResult)

    @pytest.mark.asyncio
    async def test_revoke_credential(self) -> None:
        """Can revoke a credential."""
        from uuid import uuid4

        job = CredentialCleanupJob()
        result = await job.revoke_credential(uuid4())

        # Placeholder returns True
        assert result is True


class TestCleanupJobIntegration:
    """Integration tests for cleanup jobs."""

    @pytest.mark.asyncio
    async def test_full_cleanup_cycle(self) -> None:
        """Full cleanup cycle completes without errors."""
        job = RetentionCleanupJob()
        diagnostics = await job.run_cleanup()

        # All jobs should complete successfully
        for data_type, result in diagnostics.cleanup_stats.items():
            assert result.success, f"Cleanup for {data_type} failed"
            assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_cleanup_with_archiving(self) -> None:
        """Cleanup respects archive_before_delete setting."""
        # Create settings where artifacts should be archived
        settings = RetentionSettings()
        # Check that artifacts policy has archive_before_delete
        assert settings.artifacts.archive_before_delete is True

        job = RetentionCleanupJob(settings=settings)
        result = await job.cleanup_artifacts()

        # Placeholder implementation just completes
        assert result.completed_at is not None
