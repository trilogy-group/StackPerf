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
        TaskCard,
        Variant,
    )

    # Test basic instantiation
    provider = ProviderConfig(
        name="test-provider",
        api_key_env="TEST_API_KEY",
    )
    assert provider.name == "test-provider"

    harness = HarnessProfile(
        name="test-harness",
        protocol="openai",
    )
    assert harness.protocol == "openai"

    variant = Variant(
        name="test-variant",
        provider="test-provider",
        model="gpt-4",
        harness_profile="test-harness",
    )
    assert variant.model == "gpt-4"

    experiment = Experiment(
        name="test-experiment",
        description="Test experiment",
    )
    assert experiment.name == "test-experiment"

    task_card = TaskCard(
        id="test-task",
        description="Test task",
    )
    assert task_card.id == "test-task"


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
