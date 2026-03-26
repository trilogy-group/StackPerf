"""Domain models for sessions, requests, and metric rollups."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(UTC)


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
    proxy_credential_id: str | None = Field(
        default=None,
        description="Session-scoped proxy credential",
    )
    started_at: datetime = Field(default_factory=_utc_now)
    ended_at: datetime | None = Field(default=None)
    status: str = Field(default="active", description="Session status")


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
