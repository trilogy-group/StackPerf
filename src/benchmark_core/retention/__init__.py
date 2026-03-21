"""Retention policy management for benchmark data.

This module provides retention controls for managing the lifecycle
of benchmark data, ensuring compliance with data governance requirements.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class DataType(str, Enum):
    """Types of benchmark data with retention policies."""

    RAW_INGESTION = "raw_ingestion"
    NORMALIZED_REQUESTS = "normalized_requests"
    SESSION_CREDENTIALS = "session_credentials"
    ARTIFACTS = "artifacts"
    ROLLUPS = "rollups"


@dataclass
class RetentionPolicy:
    """Retention policy for a specific data type.

    Attributes:
        data_type: Type of data this policy applies to.
        retention_days: Number of days to retain data.
        delete_after_retention: Whether to delete data after retention period.
        archive_before_delete: Whether to archive data before deletion.
    """

    data_type: DataType
    retention_days: int
    delete_after_retention: bool = True
    archive_before_delete: bool = False

    def is_expired(self, created_at: datetime) -> bool:
        """Check if data with the given creation timestamp is expired.

        Args:
            created_at: Creation timestamp of the data.

        Returns:
            True if the data is past its retention period.
        """
        expiration = created_at + timedelta(days=self.retention_days)
        return datetime.utcnow() > expiration

    def get_expiration_date(self, created_at: datetime) -> datetime:
        """Get the expiration date for data with the given creation timestamp.

        Args:
            created_at: Creation timestamp of the data.

        Returns:
            Expiration datetime.
        """
        return created_at + timedelta(days=self.retention_days)


@dataclass
class RetentionSettings:
    """Complete retention settings for all benchmark data types.

    This class defines default retention policies that can be customized
    per deployment. Default values are designed for typical benchmarking
    workflows while maintaining auditability.
    """

    policies: dict[DataType, RetentionPolicy]

    @classmethod
    def defaults(cls) -> "RetentionSettings":
        """Create retention settings with default policies.

        Default retention periods:
        - Raw ingestion: 7 days (short-lived, high volume)
        - Normalized requests: 30 days (queryable for recent sessions)
        - Session credentials: 1 day (security best practice)
        - Artifacts: 90 days (exported reports may be needed for audits)
        - Rollups: 365 days (aggregated data for long-term trends)
        """
        return cls(
            policies={
                DataType.RAW_INGESTION: RetentionPolicy(
                    data_type=DataType.RAW_INGESTION,
                    retention_days=7,
                    delete_after_retention=True,
                ),
                DataType.NORMALIZED_REQUESTS: RetentionPolicy(
                    data_type=DataType.NORMALIZED_REQUESTS,
                    retention_days=30,
                    delete_after_retention=True,
                ),
                DataType.SESSION_CREDENTIALS: RetentionPolicy(
                    data_type=DataType.SESSION_CREDENTIALS,
                    retention_days=1,
                    delete_after_retention=True,
                ),
                DataType.ARTIFACTS: RetentionPolicy(
                    data_type=DataType.ARTIFACTS,
                    retention_days=90,
                    delete_after_retention=False,
                    archive_before_delete=True,
                ),
                DataType.ROLLUPS: RetentionPolicy(
                    data_type=DataType.ROLLUPS,
                    retention_days=365,
                    delete_after_retention=False,
                ),
            }
        )

    def get_policy(self, data_type: DataType) -> RetentionPolicy:
        """Get retention policy for a specific data type.

        Args:
            data_type: Type of data.

        Returns:
            Retention policy for the data type.
        """
        return self.policies.get(
            data_type,
            RetentionPolicy(data_type=data_type, retention_days=30),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert retention settings to a dictionary.

        Returns:
            Dictionary representation of retention settings.
        """
        return {
            "policies": {
                dt.value: {
                    "data_type": policy.data_type.value,
                    "retention_days": policy.retention_days,
                    "delete_after_retention": policy.delete_after_retention,
                    "archive_before_delete": policy.archive_before_delete,
                }
                for dt, policy in self.policies.items()
            }
        }
