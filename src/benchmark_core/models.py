"""Domain models for sessions, requests, and metric rollups."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, SecretStr


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(UTC)


class SessionOutcomeState(StrEnum):
    """Valid outcome states for a benchmark session."""

    VALID = "valid"
    INVALID = "invalid"
    ABORTED = "aborted"


class ProxyKeyStatus(StrEnum):
    """Valid status values for a proxy key registry entry."""

    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class Session(BaseModel):
    """One interactive benchmark session under one variant and one task card."""

    session_id: UUID = Field(default_factory=uuid4)
    experiment_id: str = Field(..., description="Experiment identifier")
    variant_id: str = Field(..., description="Variant identifier")
    task_card_id: str = Field(..., description="Task card identifier")
    harness_profile: str = Field(..., description="Harness profile name")
    repo_path: str = Field(..., description="Absolute repository root")
    git_branch: str = Field(..., description="Active git branch")
    git_commit: str = Field(..., description="Commit SHA")
    git_dirty: bool = Field(default=False, description="Dirty state flag")
    operator_label: str | None = Field(default=None, description="Operator-provided label")
    notes: str | None = Field(default=None, description="Session notes from operator")
    proxy_credential_alias: str | None = Field(
        default=None,
        description="Session-scoped proxy credential key alias",
    )
    proxy_credential_id: str | None = Field(
        default=None,
        description="Proxy credential identifier",
    )
    started_at: datetime = Field(default_factory=_utc_now)
    ended_at: datetime | None = Field(default=None)
    status: str = Field(default="active", description="Session status")
    outcome_state: str | None = Field(
        default=None,
        description="Outcome state: valid, invalid, or aborted",
    )


class ProxyCredential(BaseModel):
    """A session-scoped proxy credential for LiteLLM authentication.

    Stores metadata and reference information. The actual secret key
    is managed by LiteLLM and is never stored in the benchmark database.
    """

    credential_id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(..., description="Benchmark session ID")
    key_alias: str = Field(..., description="Human-readable key alias for correlation")
    # Secret is stored only in memory, never persisted to benchmark DB
    api_key: SecretStr = Field(..., description="LiteLLM API key (session-scoped)")
    # Metadata tags for joining back to session
    experiment_id: str = Field(..., description="Experiment identifier")
    variant_id: str = Field(..., description="Variant identifier")
    harness_profile: str = Field(..., description="Harness profile name")
    # Metadata tags to send to LiteLLM for correlation
    metadata_tags: dict[str, str] = Field(
        default_factory=dict,
        description="Tags for LiteLLM request correlation",
    )
    # LiteLLM-specific reference
    litellm_key_id: str | None = Field(
        default=None,
        description="LiteLLM internal key ID for revocation",
    )
    # Expiration and lifecycle
    expires_at: datetime | None = Field(
        default=None,
        description="Credential expiration time",
    )
    is_active: bool = Field(default=True, description="Credential active status")
    created_at: datetime = Field(default_factory=_utc_now)
    revoked_at: datetime | None = Field(default=None)

    def get_redacted_key(self) -> str:
        """Return a redacted version of the API key for logging."""
        key_value = self.api_key.get_secret_value()
        if len(key_value) <= 12:
            return "***"
        return f"{key_value[:4]}...{key_value[-4:]}"


class ProxyKey(BaseModel):
    """Non-secret registry entry for a LiteLLM virtual key.

    Stores metadata and reference information. The actual secret key
    is managed by LiteLLM and is never stored in the benchmark database.
    """

    proxy_key_id: UUID = Field(default_factory=uuid4)
    key_alias: str = Field(..., description="Human-readable unique key alias")
    litellm_key_id: str | None = Field(
        default=None,
        description="LiteLLM internal key ID for correlation",
    )
    owner: str | None = Field(default=None, description="Key owner label")
    team: str | None = Field(default=None, description="Team metadata")
    customer: str | None = Field(default=None, description="Customer metadata")
    purpose: str | None = Field(default=None, description="Key purpose/description")
    allowed_models: list[str] = Field(default_factory=list, description="Allowed model aliases")
    budget_duration: str | None = Field(
        default=None, description="Budget duration (e.g., daily, monthly)"
    )
    budget_amount: float | None = Field(default=None, description="Budget amount")
    budget_currency: str = Field(default="USD", description="Budget currency")
    status: ProxyKeyStatus = Field(
        default=ProxyKeyStatus.ACTIVE,
        description="Key status: active, revoked, expired",
    )
    key_metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    proxy_credential_id: UUID | None = Field(
        default=None,
        description="Optional link to session-scoped proxy credential",
    )
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime | None = Field(default=None)
    revoked_at: datetime | None = Field(default=None)
    expires_at: datetime | None = Field(default=None)


class Request(BaseModel):
    """One normalized LLM call observed through LiteLLM."""

    request_id: str = Field(..., description="LiteLLM call ID")
    session_id: UUID = Field(..., description="Benchmark session ID")
    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model identifier")
    timestamp: datetime = Field(..., description="Request timestamp (UTC)")
    latency_ms: float | None = Field(None, description="Total latency in milliseconds")
    ttft_ms: float | None = Field(None, description="Time to first token in milliseconds")
    tokens_prompt: int | None = Field(None, description="Prompt token count")
    tokens_completion: int | None = Field(None, description="Completion token count")
    error: bool = Field(default=False, description="Error flag")
    error_message: str | None = Field(None, description="Error message if applicable")
    cache_hit: bool | None = Field(None, description="Cache hit flag")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class MetricRollup(BaseModel):
    """Derived latency, throughput, error, and cache metrics."""

    rollup_id: UUID = Field(default_factory=uuid4)
    dimension_type: str = Field(..., description="request, session, variant, or experiment")
    dimension_id: str = Field(..., description="ID for the dimension")
    metric_name: str = Field(..., description="Metric name")
    metric_value: float = Field(..., description="Metric value")
    sample_count: int = Field(default=1, description="Number of samples")
    computed_at: datetime = Field(default_factory=_utc_now)


class Artifact(BaseModel):
    """Arbitrary files/data produced during a benchmark session or experiment."""

    artifact_id: UUID = Field(default_factory=uuid4)
    session_id: UUID | None = Field(
        default=None,
        description="Associated session ID (if session-scoped)",
    )
    experiment_id: UUID | None = Field(
        default=None,
        description="Associated experiment ID (if experiment-scoped)",
    )
    artifact_type: str = Field(..., description="Type of artifact (e.g., export, report, bundle)")
    name: str = Field(..., description="Artifact name")
    content_type: str = Field(..., description="MIME content type")
    storage_path: str = Field(..., description="Path to stored artifact")
    size_bytes: int | None = Field(default=None, description="Size in bytes")
    artifact_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional artifact metadata",
    )
    created_at: datetime = Field(default_factory=_utc_now)
