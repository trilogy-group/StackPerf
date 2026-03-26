"""Unit tests for collectors package."""


def test_import_collectors_package() -> None:
    """Smoke test: collectors package imports successfully."""
    import collectors

    assert collectors is not None


def test_import_litellm_collector() -> None:
    """Smoke test: LiteLLM collector imports successfully."""
    from collectors.litellm_collector import LiteLLMCollector

    # Verify class can be instantiated (with dummy params)
    collector = LiteLLMCollector(
        base_url="http://localhost:4000",
        api_key="test-key",
        repository=None,  # type: ignore
    )
    assert collector is not None


def test_import_prometheus_collector() -> None:
    """Smoke test: Prometheus collector imports successfully."""
    from collectors.prometheus_collector import PrometheusCollector

    collector = PrometheusCollector(
        base_url="http://localhost:9090",
        session_id="test-session",
    )
    assert collector is not None


def test_import_normalization() -> None:
    """Smoke test: normalization job imports successfully."""
    from collectors.normalization import NormalizationJob

    job = NormalizationJob(repository=None)  # type: ignore
    assert job is not None


def test_import_rollup_job() -> None:
    """Smoke test: rollup job imports successfully."""
    from collectors.rollup_job import RollupJob

    job = RollupJob()
    assert job is not None
