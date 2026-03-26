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

    # Verify parameterized query generation works
    sql, params = DashboardQueries.session_overview()
    assert "SELECT" in sql
    assert ":session_id" in sql  # Parameterized placeholder
    assert params == {"session_id": None}  # Template with placeholder key

    # Verify experiment summary query
    sql2, params2 = DashboardQueries.experiment_summary()
    assert "SELECT" in sql2
    assert ":experiment_id" in sql2
    assert params2 == {"experiment_id": None}

    # Verify latency distribution query
    sql3, placeholders = DashboardQueries.latency_distribution(3)
    assert "SELECT" in sql3
    assert ":session_id_0" in sql3
    assert ":session_id_1" in sql3
    assert ":session_id_2" in sql3
    assert len(placeholders) == 3
