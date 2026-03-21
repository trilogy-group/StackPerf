"""Task card configuration model."""

from typing import Annotated

from pydantic import Field

from .base import BaseConfig, NameStr


class TaskCardConfig(BaseConfig, NameStr):
    """A benchmark task definition."""

    repo_path: str | None = None
    goal: Annotated[str, Field(min_length=1)]
    starting_prompt: Annotated[str, Field(min_length=1)]
    stop_condition: Annotated[str, Field(min_length=1)]
    session_timebox_minutes: int = 30
    notes: list[str] = Field(default_factory=list)
