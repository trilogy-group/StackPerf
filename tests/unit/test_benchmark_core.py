"""Unit tests for benchmark_core package."""

from uuid import UUID


def test_import_benchmark_core() -> None:
    """Smoke test: benchmark_core package imports successfully."""
    import benchmark_core

    assert benchmark_core.__version__ == "0.1.0"


def test_import_config_models() -> None:
    """Smoke test: config models import successfully."""
    from benchmark_core.config import (
        Experiment,
        HarnessProfile,
        ProviderConfig,
        ProviderModel,
        RoutingDefaults,
        TaskCard,
        Variant,
    )

    # Test basic instantiation with new typed schemas
    provider = ProviderConfig(
        name="test-provider",
        protocol_surface="openai_responses",
        upstream_base_url_env="TEST_BASE_URL",
        api_key_env="TEST_API_KEY",
        models=[ProviderModel(alias="gpt-4o", upstream_model="gpt-4o")],
        routing_defaults=RoutingDefaults(timeout_seconds=120),
    )
    assert provider.name == "test-provider"
    assert provider.protocol_surface == "openai_responses"

    harness = HarnessProfile(
        name="test-harness",
        protocol_surface="openai_responses",
        base_url_env="BASE_URL",
        api_key_env="API_KEY",
        model_env="MODEL",
    )
    assert harness.protocol_surface == "openai_responses"

    variant = Variant(
        name="test-variant",
        provider="test-provider",
        model_alias="gpt-4o",
        harness_profile="test-harness",
        benchmark_tags={"harness": "test", "provider": "test", "model": "gpt-4o"},
    )
    assert variant.model_alias == "gpt-4o"

    experiment = Experiment(
        name="test-experiment",
        description="Test experiment",
        variants=["test-variant"],
    )
    assert experiment.name == "test-experiment"

    task_card = TaskCard(
        name="test-task",
        goal="Test task goal",
        starting_prompt="Test starting prompt",
        stop_condition="Test stop condition",
    )
    assert task_card.name == "test-task"


def test_import_domain_models() -> None:
    """Smoke test: domain models import successfully."""
    from benchmark_core.models import MetricRollup, Request, Session

    # Test Session instantiation
    session = Session(
        experiment_id="test-exp",
        variant_id="test-var",
        task_card_id="test-task",
        harness_profile="test-harness",
        repo_path="/tmp/test",
        git_branch="main",
        git_commit="abc123",
    )
    assert isinstance(session.session_id, UUID)
    assert session.status == "active"

    # Test Request instantiation
    request = Request(
        request_id="req-123",
        session_id=session.session_id,
        provider="test-provider",
        model="gpt-4",
        timestamp=session.started_at,
    )
    assert request.request_id == "req-123"

    # Test MetricRollup instantiation
    rollup = MetricRollup(
        dimension_type="session",
        dimension_id=str(session.session_id),
        metric_name="avg_latency",
        metric_value=100.0,
    )
    assert rollup.metric_name == "avg_latency"


def test_import_repositories() -> None:
    """Smoke test: repositories import successfully."""
    from benchmark_core.repositories import RequestRepository, SessionRepository

    # Verify abstract classes exist
    assert hasattr(SessionRepository, "create")
    assert hasattr(RequestRepository, "create")


def test_import_services() -> None:
    """Smoke test: services import successfully."""
    from benchmark_core.services import CredentialService

    # Verify services can be instantiated
    # Note: SessionService requires a repository
    credential_service = CredentialService()
    assert credential_service is not None
