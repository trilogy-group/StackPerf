"""Task card configuration models."""

from pydantic import BaseModel, Field

from .base import BenchmarkConfigBase


class StopCondition(BaseModel):
    """Condition for automatic session termination."""

    condition_type: str = Field(
        ..., description="Type of stop condition"
    )
    description: str = Field(
        ..., description="Human-readable description"
    )
    timeout_minutes: int | None = Field(
        None, description="Maximum session duration"
    )


class TaskCardConfig(BenchmarkConfigBase):
    """Benchmark task definition."""

    # Repository
    repo_path: str | None = Field(
        None, description="Path to target repository"
    )
    repo_url: str | None = Field(
        None, description="URL to clone if not local"
    )

    # Task definition
    goal: str = Field(
        ..., description="Benchmark objective"
    )
    starting_prompt: str | None = Field(
        None, description="Initial instructions for the session"
    )

    # Stop conditions
    stop_condition: str = Field(
        ..., description="Completion condition description"
    )
    session_timebox_minutes: int | None = Field(
        None, description="Maximum session duration"
    )

    # Constraints
    allowed_interventions: list[str] = Field(
        default_factory=list,
        description="Allowed operator interventions",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Task constraints and restrictions",
    )

    # Notes
    notes: list[str] = Field(
        default_factory=list,
        description="Additional task notes",
    )
