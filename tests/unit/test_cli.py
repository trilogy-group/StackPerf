"""Unit tests for CLI package."""


def test_import_cli_package() -> None:
    """Smoke test: CLI package imports successfully."""
    import cli

    assert cli is not None


def test_import_main_app() -> None:
    """Smoke test: main CLI app imports successfully."""
    from cli.main import app

    assert app is not None


def test_import_commands() -> None:
    """Smoke test: command modules import successfully."""
    from cli.commands import config, export, session

    assert config.app is not None
    assert session.app is not None
    assert export.app is not None
