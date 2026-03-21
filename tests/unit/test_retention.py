"""Unit tests for retention controls.

Tests verify that retention settings are documented and enforceable.
"""

from datetime import datetime, timedelta

from src.benchmark_core.retention import (
    DataType,
    RetentionPolicy,
    RetentionSettings,
)


class TestRetentionPolicy:
    """Test retention policy behavior."""

    def test_policy_is_expired_for_old_data(self) -> None:
        """Policy should identify data past retention window."""
        policy = RetentionPolicy(
            data_type=DataType.RAW_INGESTION,
            retention_days=7,
        )
        old_date = datetime.utcnow() - timedelta(days=10)
        assert policy.is_expired(old_date) is True

    def test_policy_not_expired_for_recent_data(self) -> None:
        """Policy should not expire data within retention window."""
        policy = RetentionPolicy(
            data_type=DataType.RAW_INGESTION,
            retention_days=30,
        )
        recent_date = datetime.utcnow() - timedelta(days=1)
        assert policy.is_expired(recent_date) is False

    def test_get_expiration_date(self) -> None:
        """Should calculate correct expiration date."""
        policy = RetentionPolicy(
            data_type=DataType.NORMALIZED_REQUESTS,
            retention_days=30,
        )
        created = datetime(2024, 1, 1)
        expected = datetime(2024, 1, 31)
        assert policy.get_expiration_date(created) == expected


class TestRetentionSettings:
    """Test retention settings configuration."""

    def test_defaults_creates_settings(self) -> None:
        """Defaults factory should create valid settings."""
        settings = RetentionSettings.defaults()
        assert settings is not None

    def test_defaults_has_all_data_types(self) -> None:
        """Default settings should cover all data types."""
        settings = RetentionSettings.defaults()
        for data_type in DataType:
            assert data_type in settings.policies

    def test_raw_ingestion_default_is_short(self) -> None:
        """Raw ingestion should have short default retention."""
        settings = RetentionSettings.defaults()
        policy = settings.get_policy(DataType.RAW_INGESTION)
        assert policy.retention_days <= 14  # Default is 7 days

    def test_session_credentials_default_is_minimal(self) -> None:
        """Session credentials should have minimal retention."""
        settings = RetentionSettings.defaults()
        policy = settings.get_policy(DataType.SESSION_CREDENTIALS)
        assert policy.retention_days <= 1

    def test_rollups_default_is_long(self) -> None:
        """Rollups should have long retention for trends."""
        settings = RetentionSettings.defaults()
        policy = settings.get_policy(DataType.ROLLUPS)
        assert policy.retention_days >= 365

    def test_artifacts_default_includes_archive(self) -> None:
        """Artifacts should be archived by default."""
        settings = RetentionSettings.defaults()
        policy = settings.get_policy(DataType.ARTIFACTS)
        assert policy.archive_before_delete is True

    def test_to_dict_provides_documentation(self) -> None:
        """Settings should serialize for documentation."""
        settings = RetentionSettings.defaults()
        result = settings.to_dict()
        assert "policies" in result
        assert DataType.RAW_INGESTION.value in result["policies"]


class TestDataTypeEnum:
    """Test DataType enum values."""

    def test_all_data_types_exist(self) -> None:
        """All expected data types should be defined."""
        expected = {
            "raw_ingestion",
            "normalized_requests",
            "session_credentials",
            "artifacts",
            "rollups",
        }
        actual = {dt.value for dt in DataType}
        assert expected == actual
