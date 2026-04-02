"""Unit tests for diagnostic messages.

Tests verify that diagnostics point directly to the failing configuration
or service (acceptance criterion).
"""

from benchmark_core.services.health_service import (
    HealthCheckResult,
    HealthStatus,
)


class TestHealthCheckResult:
    """Test health check result structure."""

    def test_result_has_component(self) -> None:
        """Result should have component name."""
        result = HealthCheckResult(
            component="Test",
            status=HealthStatus.HEALTHY,
            message="OK",
        )
        assert result.component == "Test"

    def test_result_has_status(self) -> None:
        """Result should have status."""
        result = HealthCheckResult(
            component="Test",
            status=HealthStatus.UNHEALTHY,
            message="Failed",
        )
        assert result.status == HealthStatus.UNHEALTHY

    def test_result_has_message(self) -> None:
        """Result should have message."""
        result = HealthCheckResult(
            component="Test",
            status=HealthStatus.HEALTHY,
            message="Connection successful",
        )
        assert result.message == "Connection successful"

    def test_result_has_action(self) -> None:
        """Result should have suggested action for failures."""
        result = HealthCheckResult(
            component="LiteLLM",
            status=HealthStatus.UNHEALTHY,
            message="Cannot connect",
            action="Ensure LiteLLM is running: docker-compose up -d litellm",
        )
        assert result.action is not None
        assert "docker-compose" in result.action


class TestDiagnosticMessagesActionable:
    """Test that diagnostic messages are actionable.

    Acceptance criterion: Diagnostics point directly to the failing
    configuration or service.
    """

    def test_unhealthy_result_has_action(self) -> None:
        """Unhealthy results should include suggested action."""
        result = HealthCheckResult(
            component="PostgreSQL",
            status=HealthStatus.UNHEALTHY,
            message="Connection refused",
            action="Ensure PostgreSQL is running: docker-compose up -d postgres",
        )
        assert result.status == HealthStatus.UNHEALTHY
        assert result.action is not None
        assert "docker-compose" in result.action.lower() or "running" in result.action.lower()

    def test_connect_error_points_to_service(self) -> None:
        """Connection errors should point to the specific service."""
        result = HealthCheckResult(
            component="LiteLLM Proxy",
            status=HealthStatus.UNHEALTHY,
            message="Cannot connect to proxy",
            action="Ensure LiteLLM is running: docker-compose up -d litellm",
        )
        assert "LiteLLM" in result.action

    def test_auth_error_points_to_config(self) -> None:
        """Auth errors should point to configuration."""
        result = HealthCheckResult(
            component="LiteLLM Proxy",
            status=HealthStatus.UNHEALTHY,
            message="Authentication failed",
            action="Check LITELLM_MASTER_KEY in .env file",
        )
        assert "LITELLM_MASTER_KEY" in result.action or ".env" in result.action


class TestHealthStatusEnum:
    """Test HealthStatus enum values."""

    def test_healthy_value(self) -> None:
        """HEALTHY should have correct value."""
        assert HealthStatus.HEALTHY.value == "healthy"

    def test_unhealthy_value(self) -> None:
        """UNHEALTHY should have correct value."""
        assert HealthStatus.UNHEALTHY.value == "unhealthy"

    def test_unknown_value(self) -> None:
        """UNKNOWN should have correct value."""
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_not_configured_value(self) -> None:
        """NOT_CONFIGURED should have correct value."""
        assert HealthStatus.NOT_CONFIGURED.value == "not_configured"
