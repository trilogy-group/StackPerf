"""Task card configuration model."""

from typing import Annotated, Any

from pydantic import Field

from .base import BaseConfig, NameStr


class TaskCardConfig(BaseConfig, NameStr):
    """A benchmark task definition."""

    description: str | None = None
    repo_path: str | None = None
    goal: Annotated[str, Field(min_length=1)]
    starting_prompt: Annotated[str, Field(min_length=1)]
    stop_condition: Annotated[str, Field(min_length=1)]
    session_timebox_minutes: int = 30
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
