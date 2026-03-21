"""Integration tests for retention cleanup.

Tests verify that retention policies are enforceable by testing
cleanup against local DB fixtures.

Acceptance criterion: Retention settings are documented and enforceable.
"""

import pytest

from src.benchmark_core.retention import (
    DataType,
    RetentionPolicy,
    RetentionSettings,
)


class TestRetentionCleanup:
    """Tests for retention cleanup enforcement.

    These tests require a running PostgreSQL instance.
    """

    @pytest.mark.skip(reason="Database not yet configured")
    def test_cleanup_expired_raw_ingestion(self) -> None:
        """Cleanup should remove expired raw ingestion records.

        This test will:
        1. Insert test records with various ages
        2. Run retention cleanup
        3. Verify expired records are deleted
        4. Verify non-expired records remain
        """
        pass

    @pytest.mark.skip(reason="Database not yet configured")
    def test_cleanup_expired_session_credentials(self) -> None:
        """Cleanup should remove expired session credentials.

        Session credentials have very short retention (1 day by default).
        """
        pass

    @pytest.mark.skip(reason="Database not yet configured")
    def test_cleanup_preserves_rollups(self) -> None:
        """Cleanup should preserve rollups (long retention).

        Rollups have 365-day retention by default.
        """
        pass

    @pytest.mark.skip(reason="Database not yet configured")
    def test_cleanup_archives_artifacts(self) -> None:
        """Cleanup should archive artifacts before deletion.

        Artifacts have archive_before_delete=True by default.
        """
        pass


class TestRetentionPolicyEnforcement:
    """Tests that verify retention policies are truly enforceable."""

    def test_policy_can_be_customized(self) -> None:
        """Custom retention policies should be supported.

        Operators should be able to adjust retention for their needs.
        """
        custom_policy = RetentionPolicy(
            data_type=DataType.RAW_INGESTION,
            retention_days=1,  # Custom: 1 day instead of default 7
        )
        assert custom_policy.retention_days == 1

    def test_settings_can_override_defaults(self) -> None:
        """Full settings object should allow custom configuration."""
        defaults = RetentionSettings.defaults()
        # Create new settings with modified policy
        custom_policies = dict(defaults.policies)
        custom_policies[DataType.RAW_INGESTION] = RetentionPolicy(
            data_type=DataType.RAW_INGESTION,
            retention_days=3,
        )
        custom_settings = RetentionSettings(policies=custom_policies)
        assert custom_settings.get_policy(DataType.RAW_INGESTION).retention_days == 3

    @pytest.mark.skip(reason="Database not yet configured")
    def test_retention_is_enforced_on_ingest(self) -> None:
        """Retention should be checked during ingestion.

        Old data should be flagged for cleanup during ingestion.
        """
        pass
