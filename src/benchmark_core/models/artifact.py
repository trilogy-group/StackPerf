"""Artifact registry models."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from uuid6 import uuid7


class ArtifactType(str, Enum):
    """Types of artifacts that can be attached to sessions or experiments."""

    SESSION_EXPORT = "session_export"
    EXPERIMENT_REPORT = "experiment_report"
    REQUEST_LOG = "request_log"
    METRIC_ROLLUP = "metric_rollup"
    RAW_INGEST = "raw_ingest"
    CONFIG_SNAPSHOT = "config_snapshot"
    CUSTOM = "custom"


class Artifact(BaseModel):
    """Exported or attached artifact record."""

    artifact_id: UUID = Field(default_factory=uuid7)
    session_id: UUID | None = Field(None, description="Linked session")
    experiment_id: UUID | None = Field(None, description="Linked experiment")

    artifact_type: ArtifactType = Field(..., description="Type of artifact")
    name: str = Field(..., description="Human-readable name")
    description: str | None = Field(None, description="Artifact description")

    # Storage
    storage_path: str = Field(..., description="Path to artifact file")
    content_type: str = Field(..., description="MIME type or format")
    size_bytes: int | None = Field(None, description="File size if known")

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str | None = Field(None, description="Creator identifier")

    def is_session_artifact(self) -> bool:
        """Check if artifact is attached to a session."""
        return self.session_id is not None

    def is_experiment_artifact(self) -> bool:
        """Check if artifact is attached to an experiment."""
        return self.experiment_id is not None
