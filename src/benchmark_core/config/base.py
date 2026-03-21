"""Base configuration model with common validation."""

from pathlib import Path
from typing import Annotated

import yaml
from pydantic import BaseModel, ConfigDict, Field


class BaseConfig(BaseModel):
    """Base configuration model with strict validation."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class NameStr(BaseModel):
    """Mixin for named configuration items."""

    name: Annotated[str, Field(min_length=1, max_length=255, pattern=r"^[a-z0-9][a-z0-9-]*$")]


def load_yaml_config(path: Path) -> dict:
    """Load and parse a YAML configuration file."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with path.open("r") as f:
        data = yaml.safe_load(f)
    
    if data is None:
        return {}
    
    return data
