"""Import smoke tests for each top-level package."""

import pytest


def test_import_benchmark_core() -> None:
    """Smoke test: benchmark_core package imports without error."""
    import benchmark_core

    assert benchmark_core.__version__ == "0.1.0"


def test_import_cli() -> None:
    """Smoke test: cli package imports without error."""
    import cli

    assert hasattr(cli, "main")


def test_import_collectors() -> None:
    """Smoke test: collectors package imports without error."""
    import collectors


def test_import_reporting() -> None:
    """Smoke test: reporting package imports without error."""
    import reporting


def test_import_api() -> None:
    """Smoke test: api package imports without error."""
    import api
