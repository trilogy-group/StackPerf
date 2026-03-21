"""Canonical domain models for benchmark entities.

Based on docs/data-model-and-observability.md schema.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """Session lifecycle status."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    ABORTED = "aborted"
    INVALID = "invalid"


class RequestStatus(str, Enum):
    """Request completion status."""
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class RollupScopeType(str, Enum):
    """Rollup aggregation scope."""
    REQUEST = "request"
    SESSION = "session"
    VARIANT = "variant"
    EXPERIMENT = "experiment"


class Provider(BaseModel):
    """Upstream inference provider definition."""
    provider_id: UUID = Field(default_factory=uuid4)
    name: str
    route_name: str
    protocol_surface: str
    upstream_base_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HarnessProfile(BaseModel):
    """Harness connection profile."""
    harness_profile_id: UUID = Field(default_factory=uuid4)
    name: str
    protocol_surface: str
    base_url_env: str
    api_key_env: str
    model_env: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Variant(BaseModel):
    """Benchmarkable configuration variant."""
    variant_id: UUID = Field(default_factory=uuid4)
    name: str
    provider_id: UUID
    model_alias: str
    harness_profile_id: UUID
    config_fingerprint: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Experiment(BaseModel):
    """Named comparison grouping."""
    experiment_id: UUID = Field(default_factory=uuid4)
    name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TaskCard(BaseModel):
    """Benchmark task definition."""
    task_card_id: UUID = Field(default_factory=uuid4)
    name: str
    repo_path: Optional[str] = None
    goal: Optional[str] = None
    stop_condition: Optional[str] = None
    session_timebox_minutes: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Session(BaseModel):
    """Interactive benchmark execution."""
    session_id: UUID = Field(default_factory=uuid4)
    experiment_id: UUID
    variant_id: UUID
    task_card_id: UUID
    harness_profile_id: UUID
    status: SessionStatus = SessionStatus.PENDING
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    operator_label: Optional[str] = None
    repo_root: Optional[str] = None
    git_branch: Optional[str] = None
    git_commit_sha: Optional[str] = None
    git_dirty: Optional[bool] = None
    proxy_key_alias: Optional[str] = None
    proxy_virtual_key_id: Optional[str] = None


class Request(BaseModel):
    """Normalized LLM call."""
    request_id: UUID = Field(default_factory=uuid4)
    session_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    variant_id: Optional[UUID] = None
    provider_id: Optional[UUID] = None
    provider_route: Optional[str] = None
    model: Optional[str] = None
    harness_profile_id: Optional[UUID] = None
    litellm_call_id: Optional[str] = None
    provider_request_id: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    latency_ms: Optional[float] = None
    ttft_ms: Optional[float] = None
    proxy_overhead_ms: Optional[float] = None
    provider_latency_ms: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cached_input_tokens: Optional[int] = None
    cache_write_tokens: Optional[int] = None
    status: RequestStatus = RequestStatus.SUCCESS
    error_code: Optional[str] = None


class MetricRollup(BaseModel):
    """Derived metric summary."""
    rollup_id: UUID = Field(default_factory=uuid4)
    scope_type: RollupScopeType
    scope_id: UUID
    metric_name: str
    metric_value: float
    computed_at: datetime = Field(default_factory=datetime.utcnow)
    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None


class Artifact(BaseModel):
    """Exported report or bundle."""
    artifact_id: UUID = Field(default_factory=uuid4)
    session_id: Optional[UUID] = None
    experiment_id: Optional[UUID] = None
    artifact_type: str
    storage_path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
