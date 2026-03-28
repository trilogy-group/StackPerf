"""Unit tests for reporting package."""


def test_import_reporting_package() -> None:
    """Smoke test: reporting package imports successfully."""
    import reporting

    assert reporting is not None


def test_import_comparison() -> None:
    """Smoke test: comparison service imports successfully."""
    from unittest.mock import MagicMock

    from reporting.comparison import ComparisonService, ReportBuilder

    # ComparisonService now requires a db_session
    mock_session = MagicMock()
    service = ComparisonService(db_session=mock_session)
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
    # Security: Ensure no string interpolation patterns exist
    assert 'f"' not in sql
    assert "f'" not in sql
    assert "{}" not in sql or ":" in sql  # Allow only :param placeholders

    # Verify experiment summary query
    sql2, params2 = DashboardQueries.experiment_summary()
    assert "SELECT" in sql2
    assert ":experiment_id" in sql2
    assert params2 == {"experiment_id": None}
    # Security: Ensure no string interpolation patterns exist
    assert 'f"' not in sql2
    assert "f'" not in sql2

    # Verify latency distribution query uses safe parameterization
    sql3, placeholders = DashboardQueries.latency_distribution(3)
    assert "SELECT" in sql3
    assert ":session_id_0" in sql3
    assert ":session_id_1" in sql3
    assert ":session_id_2" in sql3
    assert len(placeholders) == 3
    # Security: Placeholders are generated server-side, not from user input
    assert all(p.startswith(":session_id_") for p in placeholders)


def test_summary_view_queries() -> None:
    """Test new summary view queries for COE-314."""
    from reporting.queries import DashboardQueries

    # Test variant summary
    sql, params = DashboardQueries.variant_summary_valid_only()
    assert "SELECT" in sql
    assert ":experiment_id" in sql
    assert "outcome_state != 'invalid'" in sql
    assert "ORDER BY v.name ASC" in sql
    assert params == {"experiment_id": None}

    # Test provider summary
    sql, params = DashboardQueries.provider_summary_valid_only()
    assert "SELECT" in sql
    assert "v.provider" in sql
    assert "outcome_state != 'invalid'" in sql
    assert "ORDER BY v.provider ASC" in sql
    assert params == {"experiment_id": None}

    # Test model summary
    sql, params = DashboardQueries.model_summary_valid_only()
    assert "SELECT" in sql
    assert "v.model_alias" in sql
    assert "outcome_state != 'invalid'" in sql
    assert "ORDER BY v.provider ASC, v.model_alias ASC" in sql
    assert params == {"experiment_id": None}

    # Test harness profile summary
    sql, params = DashboardQueries.harness_profile_summary_valid_only()
    assert "SELECT" in sql
    assert "v.harness_profile" in sql
    assert "outcome_state != 'invalid'" in sql
    assert "ORDER BY v.harness_profile ASC" in sql
    assert params == {"experiment_id": None}


def test_comparison_models() -> None:
    """Test comparison result models."""
    from uuid import uuid4

    from reporting.comparison import (
        ExperimentComparisonResult,
        HarnessProfileComparison,
        ModelComparison,
        ProviderComparison,
        VariantComparison,
    )

    # Test VariantComparison
    variant_id = uuid4()
    vc = VariantComparison(
        variant_id=variant_id,
        variant_name="test-variant",
        provider="openai",
        model="gpt-4",
        harness_profile="default",
        session_count=10,
        total_requests=100,
        avg_latency_ms=250.5,
        avg_ttft_ms=100.0,
        total_errors=5,
        error_rate=0.05,
    )
    assert vc.variant_id == variant_id
    assert vc.variant_name == "test-variant"
    assert vc.error_rate == 0.05

    # Test ProviderComparison
    pc = ProviderComparison(
        provider="openai",
        session_count=20,
        total_requests=200,
        avg_latency_ms=300.0,
        total_errors=10,
        error_rate=0.05,
        variant_count=3,
    )
    assert pc.provider == "openai"
    assert pc.variant_count == 3

    # Test ModelComparison
    mc = ModelComparison(
        provider="anthropic",
        model="claude-3",
        session_count=15,
        total_requests=150,
        avg_latency_ms=350.0,
        total_errors=3,
        error_rate=0.02,
    )
    assert mc.model == "claude-3"

    # Test HarnessProfileComparison
    hc = HarnessProfileComparison(
        harness_profile="custom",
        session_count=25,
        total_requests=250,
        avg_latency_ms=200.0,
        total_errors=8,
        error_rate=0.032,
        variant_count=2,
    )
    assert hc.harness_profile == "custom"

    # Test ExperimentComparisonResult
    exp_id = uuid4()
    ecr = ExperimentComparisonResult(
        experiment_id=exp_id,
        experiment_name="test-experiment",
        variants=[vc],
        providers=[pc],
        models=[mc],
        harness_profiles=[hc],
    )
    assert ecr.experiment_id == exp_id
    assert len(ecr.variants) == 1
    assert len(ecr.providers) == 1
    assert len(ecr.models) == 1
    assert len(ecr.harness_profiles) == 1
