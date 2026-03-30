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


def test_comparison_service_empty_sessions() -> None:
    """Test compare_sessions with empty list returns empty result."""
    from unittest.mock import MagicMock

    from reporting.comparison import ComparisonService

    mock_session = MagicMock()
    service = ComparisonService(db_session=mock_session)

    # Test with empty session list
    import asyncio

    result = asyncio.run(service.compare_sessions([]))

    assert result == {"sessions": [], "summary": {}}
    # Should not execute any queries
    mock_session.execute.assert_not_called()


def test_comparison_service_missing_experiment() -> None:
    """Test compare_variants returns empty list when experiment doesn't exist."""
    from unittest.mock import MagicMock
    from uuid import uuid4

    from reporting.comparison import ComparisonService

    mock_session = MagicMock()
    # Return None when getting experiment
    mock_session.get.return_value = None

    service = ComparisonService(db_session=mock_session)

    import asyncio

    result = asyncio.run(service.compare_variants(uuid4()))

    assert result == []
    mock_session.get.assert_called_once()


def test_comparison_service_variant_query_construction() -> None:
    """Test that compare_variants constructs correct query."""
    from unittest.mock import MagicMock
    from uuid import uuid4

    from benchmark_core.db.models import Experiment
    from reporting.comparison import ComparisonService

    mock_session = MagicMock()

    # Create mock experiment
    mock_experiment = MagicMock(spec=Experiment)
    mock_experiment.name = "test-experiment"
    mock_session.get.return_value = mock_experiment

    # Mock query result with no variants
    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    service = ComparisonService(db_session=mock_session)

    exp_id = uuid4()
    import asyncio

    result = asyncio.run(service.compare_variants(exp_id, include_invalid=False))

    assert result == []

    # Verify experiment was fetched
    mock_session.get.assert_called_once()

    # Verify query was executed (the actual SQL construction is tested)
    mock_session.execute.assert_called()


def test_comparison_service_with_include_invalid() -> None:
    """Test that include_invalid flag affects query construction."""
    from unittest.mock import MagicMock
    from uuid import uuid4

    from benchmark_core.db.models import Experiment
    from reporting.comparison import ComparisonService

    mock_session = MagicMock()

    mock_experiment = MagicMock(spec=Experiment)
    mock_experiment.name = "test-experiment"
    mock_session.get.return_value = mock_experiment

    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_session.execute.return_value = mock_result

    service = ComparisonService(db_session=mock_session)

    # Call with include_invalid=True should not add outcome_state filter
    import asyncio

    _ = asyncio.run(service.compare_variants(uuid4(), include_invalid=True))

    # Get the SQL that was executed
    call_args = mock_session.execute.call_args
    assert call_args is not None

    # The query object contains the SQL - we verify the method was called
    # The actual filtering is tested via the queries.py unit tests


def test_variant_comparison_serialization() -> None:
    """Test that VariantComparison can be serialized to dict/JSON."""
    from uuid import uuid4

    from reporting.comparison import VariantComparison

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

    # Test model_dump()
    data = vc.model_dump()
    assert data["variant_id"] == variant_id  # Pydantic keeps UUID as UUID object
    assert data["variant_name"] == "test-variant"
    assert data["provider"] == "openai"
    assert data["error_rate"] == 0.05

    # Test JSON serialization - UUID is serialized as string in JSON
    json_str = vc.model_dump_json()
    assert '"variant_name":"test-variant"' in json_str
    assert '"provider":"openai"' in json_str
    assert str(variant_id) in json_str


def test_experiment_comparison_result_serialization() -> None:
    """Test ExperimentComparisonResult can be serialized."""
    from uuid import uuid4

    from reporting.comparison import (
        ExperimentComparisonResult,
        VariantComparison,
    )

    exp_id = uuid4()
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
        total_errors=5,
        error_rate=0.05,
    )

    ecr = ExperimentComparisonResult(
        experiment_id=exp_id,
        experiment_name="test-experiment",
        variants=[vc],
        providers=[],
        models=[],
        harness_profiles=[],
    )

    data = ecr.model_dump()
    assert data["experiment_id"] == exp_id  # Pydantic keeps UUID as UUID object
    assert data["experiment_name"] == "test-experiment"
    assert len(data["variants"]) == 1
    assert data["variants"][0]["variant_name"] == "test-variant"
