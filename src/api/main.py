"""FastAPI application for benchmark query endpoints."""

from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="LiteLLM Benchmark API",
    description="HTTP API for querying benchmark data",
    version="0.1.0",
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/sessions")
async def list_sessions(
    experiment_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """List benchmark sessions."""
    # Placeholder: actual implementation will query repository
    return []


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    """Get session details by ID."""
    # Placeholder: actual implementation will query repository
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/experiments/{experiment_id}/comparison")
async def get_experiment_comparison(experiment_id: str) -> dict:
    """Get comparison data for an experiment."""
    # Placeholder: actual implementation will use comparison service
    return {}


@app.get("/metrics")
async def get_metrics(
    session_id: str | None = None,
    experiment_id: str | None = None,
    metric_name: str | None = None,
) -> list[dict]:
    """Get metric rollups."""
    # Placeholder: actual implementation will query repository
    return []
