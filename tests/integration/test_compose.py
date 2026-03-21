"""Integration tests for Docker Compose stack.

These tests verify the local infrastructure can be started and is healthy.
They require Docker to be running.
"""


from collections.abc import Generator

import pytest


@pytest.fixture(scope="module")
def compose_up() -> Generator[None, None, None]:
    """Start the compose stack for integration tests."""
    # This is a stub - actual implementation would start compose
    # For now, we assume compose is started manually or skip
    yield


@pytest.mark.skip(reason="Requires Docker - run manually with make compose-up")
def test_compose_up_creates_healthy_services(compose_up: None) -> None:
    """All services should become healthy after compose up."""
    # This would use docker compose ps to check health
    pass


@pytest.mark.skip(reason="Requires Docker - run manually")
def test_litellm_health_endpoint() -> None:
    """LiteLLM health endpoint should respond."""
    import httpx

    response = httpx.get("http://localhost:4000/health", timeout=5.0)
    assert response.status_code == 200


@pytest.mark.skip(reason="Requires Docker - run manually")
def test_prometheus_scrapes_litellm() -> None:
    """Prometheus should successfully scrape LiteLLM metrics."""
    import httpx

    # Check Prometheus targets endpoint
    response = httpx.get("http://localhost:9090/api/v1/targets", timeout=5.0)
    assert response.status_code == 200
    data = response.json()
    # Verify litellm target is present and healthy
    assert any(
        "litellm" in str(target.get("labels", {}))
        for target in data.get("data", {}).get("activeTargets", [])
    )


@pytest.mark.skip(reason="Requires Docker - run manually")
def test_grafana_datasource_health() -> None:
    """Grafana should have healthy datasources."""
    import httpx

    # Check Grafana datasource health
    response = httpx.get(
        "http://localhost:3000/api/datasources/health",
        auth=("admin", "stackperf-dev-admin"),
        timeout=5.0,
    )
    assert response.status_code == 200
