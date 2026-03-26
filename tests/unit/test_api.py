"""Unit tests for API package."""


def test_import_api_package() -> None:
    """Smoke test: API package imports successfully."""
    import api

    assert api is not None


def test_import_main_app() -> None:
    """Smoke test: FastAPI app imports successfully."""
    from api.main import app

    assert app is not None
    assert app.title == "LiteLLM Benchmark API"
