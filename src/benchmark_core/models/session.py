"""Session lifecycle domain models."""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from uuid6 import uuid7


class SessionStatus(str, Enum):
    """Canonical session lifecycle states.

    Status transitions:
    - pending -> active: session created, harness not yet launched
    - active -> completed: normal successful completion
    - active -> aborted: operator cancelled or external stop
    - active -> invalid: misconfiguration, wrong endpoint, or data loss
    - Any -> finalized: session end processed and rollups computed
    """

    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABORTED = "aborted"
    INVALID = "invalid"
    FINALIZED = "finalized"


class OutcomeState(str, Enum):
    """Operator-reported session outcome.

    Used for filtering comparisons and recording qualitative results.
    """

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    ERROR = "error"
    EXCLUDED = "excluded"


class GitMetadata(BaseModel):
    """Captured git repository context."""

    repo_root: str = Field(..., description="Absolute path to repository root")
    branch: str = Field(..., description="Active git branch name")
    commit_sha: str = Field(..., description="Current commit SHA")
    dirty: bool = Field(..., description="Whether working tree has uncommitted changes")
    commit_message: str | None = Field(None, description="First line of commit message")


class ProxyCredential(BaseModel):
    """Session-scoped proxy credential details."""

    key_alias: str = Field(..., description="Human-readable alias for the credential")
    virtual_key_id: str | None = Field(None, description="LiteLLM virtual key ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = Field(None, description="Credential expiration time")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata attached to credential for correlation",
    )


class Session(BaseModel):
    """Canonical session record."""

    session_id: UUID = Field(default_factory=uuid7)
    experiment_id: UUID | None = Field(None, description="Linked experiment")
    variant_id: UUID | None = Field(None, description="Linked variant")
    task_card_id: UUID | None = Field(None, description="Linked task card")
    harness_profile_id: UUID | None = Field(None, description="Harness profile used")

    status: SessionStatus = Field(default=SessionStatus.PENDING)
    outcome: OutcomeState | None = Field(None, description="Operator-reported outcome")

    operator_label: str | None = Field(None, description="Operator identifier")

    # Repository context
    git_metadata: GitMetadata | None = Field(None, description="Captured git context")

    # Proxy credential
    proxy_credential: ProxyCredential | None = Field(None, description="Session credential")

    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = Field(None, description="Session end time")

    # Notes and artifacts
    notes: list[str] = Field(default_factory=list, description="Operator notes")
    artifact_ids: list[UUID] = Field(default_factory=list, description="Attached artifacts")

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def is_active(self) -> bool:
        """Check if session can accept harness traffic."""
        return self.status in (SessionStatus.PENDING, SessionStatus.ACTIVE)

    def is_finalized(self) -> bool:
        """Check if session has been finalized."""
        return self.status == SessionStatus.FINALIZED

    def is_comparison_eligible(self) -> bool:
        """Check if session should be included in comparisons."""
        return (
            self.status == SessionStatus.FINALIZED
            and self.outcome not in (OutcomeState.EXCLUDED, OutcomeState.ERROR)
        )


class SessionCreate(BaseModel):
    """Input for creating a new session."""

    experiment_name: str | None = None
    variant_name: str | None = None
    task_card_name: str | None = None
    harness_profile_name: str | None = None
    operator_label: str | None = None

    # Git context will be captured automatically if in a git repo
    capture_git: bool = True


class SessionFinalize(BaseModel):
    """Input for finalizing a session."""

    session_id: UUID
    status: SessionStatus = SessionStatus.COMPLETED
    outcome: OutcomeState = OutcomeState.SUCCESS
    notes: list[str] = Field(default_factory=list)


class SessionNote(BaseModel):
    """Input for adding a note to a session."""

    session_id: UUID
    note: str
