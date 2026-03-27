"""FastAPI application for benchmark query endpoints."""

import os
from collections.abc import Generator
from contextlib import asynccontextmanager
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.orm import sessionmaker

from api.schemas import (
    ExperimentDetailResponse,
    ExperimentListResponse,
    ExperimentResponse,
    MetricRollupListResponse,
    MetricRollupResponse,
    RequestListResponse,
    RequestResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
    VariantListResponse,
    VariantResponse,
)
from benchmark_core.db.models import (
    Experiment,
    ExperimentVariant,
    MetricRollup,
    Variant,
)
from benchmark_core.db.models import (
    Request as RequestORM,
)
from benchmark_core.db.models import (
    Session as SessionORM,
)

# Database configuration from environment
database_url = os.getenv("DATABASE_URL", "sqlite:///./benchmark.db")

# Handle PostgreSQL URL format (convert postgres:// to postgresql+psycopg2://)
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)

DATABASE_URL = database_url

# Engine and session factory
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[SQLAlchemySession, None, None]:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DBSession = Annotated[SQLAlchemySession, Depends(get_db)]


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    """Application lifespan handler for startup/shutdown.

    Note: Tables should be created via Alembic migrations in production.
    This auto-creation is only for development/testing convenience.
    """
    # In production, use: alembic upgrade head
    # For dev/test, create tables if they don't exist
    if os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true":
        from benchmark_core.db.models import Base

        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="LiteLLM Benchmark API",
    description="HTTP API for querying benchmark data for experiments, variants, sessions, requests, and metric rollups",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


# ============================================================================
# Experiment Endpoints
# ============================================================================


@app.get("/experiments", response_model=ExperimentListResponse, tags=["experiments"])
async def list_experiments(
    db: DBSession,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ExperimentListResponse:
    """List all experiments with pagination.

    Returns a paginated list of experiments sorted by creation date (descending).
    """
    # Count total
    count_stmt = select(func.count()).select_from(Experiment)
    total = db.execute(count_stmt).scalar() or 0

    # Get paginated results
    stmt = select(Experiment).order_by(Experiment.created_at.desc()).limit(limit).offset(offset)
    results = db.execute(stmt).scalars().all()

    return ExperimentListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[ExperimentResponse.model_validate(exp) for exp in results],
    )


@app.get(
    "/experiments/{experiment_id}", response_model=ExperimentDetailResponse, tags=["experiments"]
)
async def get_experiment(experiment_id: UUID, db: DBSession) -> ExperimentDetailResponse:
    """Get experiment details by ID.

    Returns experiment with associated variant IDs and session count.
    """
    # Get experiment with variants
    stmt = select(Experiment).where(Experiment.id == experiment_id).outerjoin(ExperimentVariant)
    result = db.execute(stmt).scalars().unique().one_or_none()

    if result is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # Get variant IDs
    variant_stmt = select(ExperimentVariant.variant_id).where(
        ExperimentVariant.experiment_id == experiment_id
    )
    variant_ids = [vid for (vid,) in db.execute(variant_stmt).all()]

    # Count sessions
    session_count_stmt = (
        select(func.count())
        .select_from(SessionORM)
        .where(SessionORM.experiment_id == experiment_id)
    )
    session_count = db.execute(session_count_stmt).scalar() or 0

    response = ExperimentDetailResponse(
        id=result.id,
        name=result.name,
        description=result.description,
        created_at=result.created_at,
        updated_at=result.updated_at,
        variant_ids=variant_ids,
        session_count=session_count,
    )
    return response


# ============================================================================
# Variant Endpoints
# ============================================================================


@app.get("/variants", response_model=VariantListResponse, tags=["variants"])
async def list_variants(
    db: DBSession,
    provider: Annotated[str | None, Query(description="Filter by provider name")] = None,
    harness_profile: Annotated[str | None, Query(description="Filter by harness profile")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> VariantListResponse:
    """List variants with optional filtering.

    Supports filtering by provider and harness profile.
    """
    # Build query with filters
    stmt = select(Variant)
    count_stmt = select(func.count()).select_from(Variant)

    if provider is not None:
        stmt = stmt.where(Variant.provider == provider)
        count_stmt = count_stmt.where(Variant.provider == provider)
    if harness_profile is not None:
        stmt = stmt.where(Variant.harness_profile == harness_profile)
        count_stmt = count_stmt.where(Variant.harness_profile == harness_profile)

    # Count total
    total = db.execute(count_stmt).scalar() or 0

    # Get paginated results
    stmt = stmt.order_by(Variant.created_at.desc()).limit(limit).offset(offset)
    results = db.execute(stmt).scalars().all()

    return VariantListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[VariantResponse.model_validate(v) for v in results],
    )


@app.get("/variants/{variant_id}", response_model=VariantResponse, tags=["variants"])
async def get_variant(variant_id: UUID, db: DBSession) -> VariantResponse:
    """Get variant details by ID."""
    result = db.get(Variant, variant_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Variant not found")

    return VariantResponse.model_validate(result)


# ============================================================================
# Session Endpoints
# ============================================================================


@app.get("/sessions", response_model=SessionListResponse, tags=["sessions"])
async def list_sessions(
    db: DBSession,
    experiment_id: Annotated[UUID | None, Query(description="Filter by experiment ID")] = None,
    variant_id: Annotated[UUID | None, Query(description="Filter by variant ID")] = None,
    task_card_id: Annotated[UUID | None, Query(description="Filter by task card ID")] = None,
    status: Annotated[str | None, Query(description="Filter by status")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SessionListResponse:
    """List benchmark sessions with optional filtering.

    Supports filtering by experiment, variant, task card, and status.
    """
    # Build query with filters
    stmt = select(SessionORM)
    count_stmt = select(func.count()).select_from(SessionORM)

    if experiment_id is not None:
        stmt = stmt.where(SessionORM.experiment_id == experiment_id)
        count_stmt = count_stmt.where(SessionORM.experiment_id == experiment_id)
    if variant_id is not None:
        stmt = stmt.where(SessionORM.variant_id == variant_id)
        count_stmt = count_stmt.where(SessionORM.variant_id == variant_id)
    if task_card_id is not None:
        stmt = stmt.where(SessionORM.task_card_id == task_card_id)
        count_stmt = count_stmt.where(SessionORM.task_card_id == task_card_id)
    if status is not None:
        stmt = stmt.where(SessionORM.status == status)
        count_stmt = count_stmt.where(SessionORM.status == status)

    # Count total
    total = db.execute(count_stmt).scalar() or 0

    # Get paginated results
    stmt = stmt.order_by(SessionORM.created_at.desc()).limit(limit).offset(offset)
    results = db.execute(stmt).scalars().all()

    return SessionListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[SessionResponse.model_validate(s) for s in results],
    )


@app.get("/sessions/{session_id}", response_model=SessionDetailResponse, tags=["sessions"])
async def get_session(session_id: UUID, db: DBSession) -> SessionDetailResponse:
    """Get session details by ID.

    Returns session with related entity names and request count.
    """
    from sqlalchemy.orm import joinedload

    # Get session with relationships
    stmt = (
        select(SessionORM)
        .where(SessionORM.id == session_id)
        .options(
            joinedload(SessionORM.experiment),
            joinedload(SessionORM.variant),
        )
    )
    result = db.execute(stmt).scalars().unique().one_or_none()

    if result is None:
        raise HTTPException(status_code=404, detail="Session not found")

    # Count requests
    request_count_stmt = (
        select(func.count()).select_from(RequestORM).where(RequestORM.session_id == session_id)
    )
    request_count = db.execute(request_count_stmt).scalar() or 0

    response = SessionDetailResponse(
        id=result.id,
        experiment_id=result.experiment_id,
        variant_id=result.variant_id,
        task_card_id=result.task_card_id,
        harness_profile=result.harness_profile,
        repo_path=result.repo_path,
        git_branch=result.git_branch,
        git_commit=result.git_commit,
        git_dirty=result.git_dirty,
        operator_label=result.operator_label,
        proxy_credential_id=result.proxy_credential_id,
        started_at=result.started_at,
        ended_at=result.ended_at,
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
        experiment_name=result.experiment.name if result.experiment else None,
        variant_name=result.variant.name if result.variant else None,
        task_card_name=None,  # Would need joinedload for task_card
        request_count=request_count,
    )
    return response


# ============================================================================
# Request Endpoints
# ============================================================================


@app.get("/requests", response_model=RequestListResponse, tags=["requests"])
async def list_requests(
    db: DBSession,
    session_id: Annotated[UUID | None, Query(description="Filter by session ID")] = None,
    provider: Annotated[str | None, Query(description="Filter by provider")] = None,
    model: Annotated[str | None, Query(description="Filter by model")] = None,
    error: Annotated[bool | None, Query(description="Filter by error status")] = None,
    cache_hit: Annotated[bool | None, Query(description="Filter by cache status")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RequestListResponse:
    """List requests with optional filtering.

    Supports filtering by session, provider, model, error status, and cache status.
    Results are ordered by timestamp (ascending).
    """
    # Build query with filters
    stmt = select(RequestORM)
    count_stmt = select(func.count()).select_from(RequestORM)

    if session_id is not None:
        stmt = stmt.where(RequestORM.session_id == session_id)
        count_stmt = count_stmt.where(RequestORM.session_id == session_id)
    if provider is not None:
        stmt = stmt.where(RequestORM.provider == provider)
        count_stmt = count_stmt.where(RequestORM.provider == provider)
    if model is not None:
        stmt = stmt.where(RequestORM.model == model)
        count_stmt = count_stmt.where(RequestORM.model == model)
    if error is not None:
        stmt = stmt.where(RequestORM.error == error)
        count_stmt = count_stmt.where(RequestORM.error == error)
    if cache_hit is not None:
        stmt = stmt.where(RequestORM.cache_hit == cache_hit)
        count_stmt = count_stmt.where(RequestORM.cache_hit == cache_hit)

    # Count total
    total = db.execute(count_stmt).scalar() or 0

    # Get paginated results ordered by timestamp
    stmt = stmt.order_by(RequestORM.timestamp.asc()).limit(limit).offset(offset)
    results = db.execute(stmt).scalars().all()

    return RequestListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[RequestResponse.model_validate(r) for r in results],
    )


@app.get("/requests/{request_id}", response_model=RequestResponse, tags=["requests"])
async def get_request(request_id: UUID, db: DBSession) -> RequestResponse:
    """Get request details by ID."""
    result = db.get(RequestORM, request_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Request not found")

    return RequestResponse.model_validate(result)


# ============================================================================
# Metric Rollup Endpoints
# ============================================================================


@app.get("/rollups", response_model=MetricRollupListResponse, tags=["rollups"])
async def list_rollups(
    db: DBSession,
    dimension_type: Annotated[
        str | None,
        Query(description="Filter by dimension type (request, session, variant, experiment)"),
    ] = None,
    dimension_id: Annotated[str | None, Query(description="Filter by dimension ID")] = None,
    metric_name: Annotated[str | None, Query(description="Filter by metric name")] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MetricRollupListResponse:
    """List metric rollups with optional filtering.

    Supports filtering by dimension type, dimension ID, and metric name.
    """
    # Build query with filters
    stmt = select(MetricRollup)
    count_stmt = select(func.count()).select_from(MetricRollup)

    if dimension_type is not None:
        stmt = stmt.where(MetricRollup.dimension_type == dimension_type)
        count_stmt = count_stmt.where(MetricRollup.dimension_type == dimension_type)
    if dimension_id is not None:
        stmt = stmt.where(MetricRollup.dimension_id == dimension_id)
        count_stmt = count_stmt.where(MetricRollup.dimension_id == dimension_id)
    if metric_name is not None:
        stmt = stmt.where(MetricRollup.metric_name == metric_name)
        count_stmt = count_stmt.where(MetricRollup.metric_name == metric_name)

    # Count total
    total = db.execute(count_stmt).scalar() or 0

    # Get paginated results
    stmt = stmt.order_by(MetricRollup.computed_at.desc()).limit(limit).offset(offset)
    results = db.execute(stmt).scalars().all()

    return MetricRollupListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[MetricRollupResponse.model_validate(r) for r in results],
    )


@app.get("/rollups/{rollup_id}", response_model=MetricRollupResponse, tags=["rollups"])
async def get_rollup(rollup_id: UUID, db: DBSession) -> MetricRollupResponse:
    """Get metric rollup details by ID."""
    result = db.get(MetricRollup, rollup_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Rollup not found")

    return MetricRollupResponse.model_validate(result)


# ============================================================================
# Comparison Endpoint (legacy support)
# ============================================================================


@app.get("/experiments/{experiment_id}/comparison", tags=["experiments"])
async def get_experiment_comparison(experiment_id: UUID, db: DBSession) -> dict[str, Any]:
    """Get comparison data for an experiment.

    Returns variant-level aggregations for the experiment.
    """
    # Verify experiment exists
    experiment = db.get(Experiment, experiment_id)
    if experiment is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    # Get variant-level metrics for this experiment
    stmt = (
        select(
            Variant.id.label("variant_id"),
            Variant.name.label("variant_name"),
            func.count(func.distinct(SessionORM.id)).label("session_count"),
            func.count(RequestORM.id).label("total_requests"),
            func.avg(RequestORM.latency_ms).label("avg_latency_ms"),
            func.avg(RequestORM.ttft_ms).label("avg_ttft_ms"),
            func.sum(func.case((RequestORM.error.is_(True), 1), else_=0)).label("total_errors"),
        )
        .select_from(Variant)
        .outerjoin(SessionORM, SessionORM.variant_id == Variant.id)
        .outerjoin(RequestORM, RequestORM.session_id == SessionORM.id)
        .where(SessionORM.experiment_id == experiment_id)
        .group_by(Variant.id, Variant.name)
    )

    results = db.execute(stmt).all()

    variants = []
    for row in results:
        variants.append(
            {
                "variant_id": str(row.variant_id),
                "variant_name": row.variant_name,
                "session_count": row.session_count or 0,
                "total_requests": row.total_requests or 0,
                "avg_latency_ms": row.avg_latency_ms,
                "avg_ttft_ms": row.avg_ttft_ms,
                "total_errors": row.total_errors or 0,
            }
        )

    return {
        "experiment_id": str(experiment_id),
        "experiment_name": experiment.name,
        "variants": variants,
    }


# ============================================================================
# Legacy metrics endpoint (backward compatibility)
# ============================================================================


@app.get("/metrics", tags=["rollups"])
async def get_metrics(
    db: DBSession,
    session_id: Annotated[str | None, Query(description="Filter by session ID")] = None,
    experiment_id: Annotated[str | None, Query(description="Filter by experiment ID")] = None,
    rollup_type: Annotated[
        str | None,
        Query(description="Metric rollup granularity (request, session, variant, experiment)"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[dict[str, Any]]:
    """Get metric rollups (legacy endpoint).

    Prefer using /rollups endpoint with proper filtering.
    """
    stmt = select(MetricRollup)

    if session_id is not None:
        stmt = stmt.where(MetricRollup.dimension_id == session_id)
    if experiment_id is not None:
        stmt = stmt.where(MetricRollup.dimension_id == experiment_id)
    if rollup_type is not None:
        stmt = stmt.where(MetricRollup.dimension_type == rollup_type)

    stmt = stmt.limit(limit)
    results = db.execute(stmt).scalars().all()

    return [MetricRollupResponse.model_validate(r).model_dump() for r in results]
