"""Pydantic response schemas for benchmark API endpoints."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# Base response schemas
class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""

    limit: int = Field(default=100, ge=1, le=1000, description="Max items to return")
    offset: int = Field(default=0, ge=0, description="Items to skip")


class PaginatedResponse(BaseModel):
    """Base response for paginated lists."""

    total: int = Field(..., description="Total count of items")
    limit: int = Field(..., description="Requested limit")
    offset: int = Field(..., description="Requested offset")


# Experiment schemas
class ExperimentResponse(BaseModel):
    """Response schema for a single experiment."""

    id: UUID = Field(..., description="Experiment UUID")
    name: str = Field(..., description="Experiment name")
    description: str = Field(default="", description="Experiment description")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class ExperimentListResponse(PaginatedResponse):
    """Response schema for experiment list."""

    items: list[ExperimentResponse] = Field(default_factory=list, description="List of experiments")


class ExperimentDetailResponse(ExperimentResponse):
    """Detailed experiment response with variant associations."""

    variant_ids: list[UUID] = Field(default_factory=list, description="Associated variant IDs")
    session_count: int = Field(default=0, description="Number of sessions in this experiment")


# Variant schemas
class VariantResponse(BaseModel):
    """Response schema for a single variant."""

    id: UUID = Field(..., description="Variant UUID")
    name: str = Field(..., description="Variant name")
    provider: str = Field(..., description="Provider name")
    provider_route: str | None = Field(default=None, description="Provider route")
    model_alias: str = Field(..., description="Model alias")
    harness_profile: str = Field(..., description="Harness profile name")
    harness_env_overrides: dict[str, str] = Field(
        default_factory=dict, description="Harness environment overrides"
    )
    benchmark_tags: dict[str, str] = Field(default_factory=dict, description="Benchmark tags")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class VariantListResponse(PaginatedResponse):
    """Response schema for variant list."""

    items: list[VariantResponse] = Field(default_factory=list, description="List of variants")


# Session schemas
class SessionResponse(BaseModel):
    """Response schema for a single session.

    Exposes canonical fields consistently for request and session views.
    """

    id: UUID = Field(..., description="Session UUID")
    experiment_id: UUID = Field(..., description="Experiment UUID")
    variant_id: UUID = Field(..., description="Variant UUID")
    task_card_id: UUID = Field(..., description="Task card UUID")
    harness_profile: str = Field(..., description="Harness profile name")
    repo_path: str = Field(..., description="Repository path")
    git_branch: str = Field(..., description="Git branch")
    git_commit: str = Field(..., description="Git commit SHA")
    git_dirty: bool = Field(default=False, description="Git dirty state")
    operator_label: str | None = Field(default=None, description="Operator label")
    proxy_credential_id: str | None = Field(default=None, description="Proxy credential ID")
    started_at: datetime = Field(..., description="Session start timestamp")
    ended_at: datetime | None = Field(default=None, description="Session end timestamp")
    status: str = Field(default="active", description="Session status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    model_config = {"from_attributes": True}


class SessionListResponse(PaginatedResponse):
    """Response schema for session list."""

    items: list[SessionResponse] = Field(default_factory=list, description="List of sessions")


class SessionDetailResponse(SessionResponse):
    """Detailed session response with related entity names."""

    experiment_name: str | None = Field(default=None, description="Experiment name")
    variant_name: str | None = Field(default=None, description="Variant name")
    task_card_name: str | None = Field(default=None, description="Task card name")
    request_count: int = Field(default=0, description="Number of requests in this session")


# Request schemas
class RequestResponse(BaseModel):
    """Response schema for a single request.

    Exposes canonical fields consistently for request and session views.
    """

    id: UUID = Field(..., description="Request UUID (internal)")
    request_id: str = Field(..., description="LiteLLM request ID")
    session_id: UUID = Field(..., description="Session UUID")
    provider: str = Field(..., description="Provider name")
    model: str = Field(..., description="Model name")
    timestamp: datetime = Field(..., description="Request timestamp (UTC)")
    latency_ms: float | None = Field(default=None, description="Total latency in ms")
    ttft_ms: float | None = Field(default=None, description="Time to first token in ms")
    tokens_prompt: int | None = Field(default=None, description="Prompt token count")
    tokens_completion: int | None = Field(default=None, description="Completion token count")
    error: bool = Field(default=False, description="Error flag")
    error_message: str | None = Field(default=None, description="Error message")
    cache_hit: bool | None = Field(default=None, description="Cache hit flag")
    request_metadata: dict[str, Any] = Field(default_factory=dict, description="Request metadata")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}


class RequestListResponse(PaginatedResponse):
    """Response schema for request list."""

    items: list[RequestResponse] = Field(default_factory=list, description="List of requests")


# MetricRollup schemas
class MetricRollupResponse(BaseModel):
    """Response schema for a single metric rollup."""

    id: UUID = Field(..., description="Rollup UUID")
    dimension_type: str = Field(
        ..., description="Dimension type (request, session, variant, experiment)"
    )
    dimension_id: str = Field(..., description="Dimension ID")
    metric_name: str = Field(..., description="Metric name")
    metric_value: float = Field(..., description="Metric value")
    sample_count: int = Field(default=1, description="Number of samples")
    computed_at: datetime = Field(..., description="Computation timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {"from_attributes": True}


class MetricRollupListResponse(PaginatedResponse):
    """Response schema for metric rollup list."""

    items: list[MetricRollupResponse] = Field(default_factory=list, description="List of rollups")


# Filter schemas for query parameters
class SessionFilter(BaseModel):
    """Filter parameters for session queries."""

    experiment_id: UUID | None = Field(default=None, description="Filter by experiment ID")
    variant_id: UUID | None = Field(default=None, description="Filter by variant ID")
    task_card_id: UUID | None = Field(default=None, description="Filter by task card ID")
    status: str | None = Field(default=None, description="Filter by status")


class RequestFilter(BaseModel):
    """Filter parameters for request queries."""

    session_id: UUID | None = Field(default=None, description="Filter by session ID")
    provider: str | None = Field(default=None, description="Filter by provider")
    model: str | None = Field(default=None, description="Filter by model")
    error: bool | None = Field(default=None, description="Filter by error status")
    cache_hit: bool | None = Field(default=None, description="Filter by cache status")


class VariantFilter(BaseModel):
    """Filter parameters for variant queries."""

    provider: str | None = Field(default=None, description="Filter by provider")
    harness_profile: str | None = Field(default=None, description="Filter by harness profile")


class MetricRollupFilter(BaseModel):
    """Filter parameters for metric rollup queries."""

    dimension_type: str | None = Field(
        default=None, description="Filter by dimension type (request, session, variant, experiment)"
    )
    dimension_id: str | None = Field(default=None, description="Filter by dimension ID")
    metric_name: str | None = Field(default=None, description="Filter by metric name")


# Comparison endpoint response schemas
class VariantComparisonResponse(BaseModel):
    """Response schema for a single variant in experiment comparison."""

    variant_id: UUID = Field(..., description="Variant UUID")
    variant_name: str = Field(..., description="Variant name")
    session_count: int = Field(default=0, description="Number of sessions")
    total_requests: int = Field(default=0, description="Total request count")
    avg_latency_ms: float | None = Field(default=None, description="Average latency in ms")
    avg_ttft_ms: float | None = Field(default=None, description="Average time to first token in ms")
    total_errors: int = Field(default=0, description="Total error count")


class ExperimentComparisonResponse(BaseModel):
    """Response schema for experiment comparison endpoint."""

    experiment_id: UUID = Field(..., description="Experiment UUID")
    experiment_name: str = Field(..., description="Experiment name")
    variants: list[VariantComparisonResponse] = Field(
        default_factory=list, description="Variant comparison data"
    )
