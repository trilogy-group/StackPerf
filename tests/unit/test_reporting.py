"""Unit tests for reporting package."""


def test_import_reporting_package() -> None:
    """Smoke test: reporting package imports successfully."""
    import reporting

    assert reporting is not None


def test_import_comparison() -> None:
    """Smoke test: comparison service imports successfully."""
    from reporting.comparison import ComparisonService, ReportBuilder

    service = ComparisonService()
    assert service is not None

    builder = ReportBuilder()
    assert builder is not None


def test_import_serialization() -> None:
    """Smoke test: serialization utilities import successfully."""
    from reporting.serialization import ReportSerializer

    assert ReportSerializer is not None


def test_import_queries() -> None:
    """Smoke test: dashboard queries import successfully."""
    from reporting.queries import DashboardQueries

    queries = DashboardQueries()
    assert queries is not None

    # Verify query methods work
    sql = DashboardQueries.session_overview("test-session")
    assert "SELECT" in sql
    assert "test-session" in sql
