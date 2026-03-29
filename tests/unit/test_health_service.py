"""Unit tests for health service."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from benchmark_core.services.health_service import (
    HealthReport,
    HealthService,
    HealthStatus,
)


@pytest.fixture
def health_service():
    """Create health service instance."""
    return HealthService()


@pytest.fixture
def temp_configs_dir():
    """Create temporary configs directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        configs_path = Path(tmpdir) / "configs"
        configs_path.mkdir()

        # Create required subdirectories
        (configs_path / "providers").mkdir()
        (configs_path / "harnesses").mkdir()
        (configs_path / "variants").mkdir()

        # Create sample config files
        (configs_path / "providers" / "test.yaml").write_text("name: test\n")
        (configs_path / "harnesses" / "test.yaml").write_text("name: test\n")
        (configs_path / "variants" / "test.yaml").write_text("name: test\n")

        yield str(configs_path)


class TestHealthService:
    """Tests for HealthService class."""

    def test_check_database_sqlite_success(self, health_service, tmp_path):
        """Test successful SQLite database check."""
        # Use temporary SQLite database
        db_path = tmp_path / "test.db"
        with patch.dict(os.environ, {"DATABASE_URL": f"sqlite:///{db_path}"}):
            result = health_service.check_database()

        assert result.status == HealthStatus.HEALTHY
        assert "SQLite" in result.message
        assert "connection successful" in result.message

    def test_check_database_connection_failure(self, health_service):
        """Test database check with connection failure."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://invalid:5432/nonexistent"}):
            # Should handle connection failure gracefully
            result = health_service.check_database()

        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message.lower()
        assert result.suggestion is not None

    def test_check_litellm_proxy_success(self, health_service):
        """Test successful LiteLLM proxy check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"status": "healthy"}

        with patch("requests.get", return_value=mock_response):
            result = health_service.check_litellm_proxy()

        assert result.status == HealthStatus.HEALTHY
        assert "healthy" in result.message.lower()

    def test_check_litellm_proxy_connection_error(self, health_service):
        """Test LiteLLM proxy check with connection error."""
        import requests
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError()):
            result = health_service.check_litellm_proxy()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Cannot connect" in result.message
        assert result.suggestion is not None

    def test_check_litellm_proxy_timeout(self, health_service):
        """Test LiteLLM proxy check with timeout."""
        import requests
        with patch("requests.get", side_effect=requests.exceptions.Timeout()):
            result = health_service.check_litellm_proxy()

        assert result.status == HealthStatus.UNHEALTHY
        assert "timed out" in result.message.lower()

    def test_check_litellm_proxy_unhealthy_status(self, health_service):
        """Test LiteLLM proxy check with unhealthy status code."""
        mock_response = MagicMock()
        mock_response.status_code = 503

        with patch("requests.get", return_value=mock_response):
            result = health_service.check_litellm_proxy()

        assert result.status == HealthStatus.UNHEALTHY
        assert "503" in result.message

    def test_check_prometheus_success(self, health_service):
        """Test successful Prometheus check."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("requests.get", return_value=mock_response):
            result = health_service.check_prometheus()

        assert result.status == HealthStatus.HEALTHY
        assert "healthy" in result.message.lower()

    def test_check_prometheus_connection_error(self, health_service):
        """Test Prometheus check with connection error."""
        import requests
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError()):
            result = health_service.check_prometheus()

        assert result.status == HealthStatus.UNHEALTHY
        assert "Cannot connect" in result.message
        assert result.suggestion is not None

    def test_check_configurations_success(self, health_service, temp_configs_dir):
        """Test successful configurations check."""
        result = health_service.check_configurations(temp_configs_dir)

        assert result.status == HealthStatus.HEALTHY
        assert "Configuration files found" in result.message

    def test_check_configurations_missing_directory(self, health_service):
        """Test configurations check with missing directory."""
        result = health_service.check_configurations("/nonexistent/path")

        assert result.status == HealthStatus.UNHEALTHY
        assert "not found" in result.message.lower()

    def test_check_configurations_missing_subdirs(self, health_service, tmp_path):
        """Test configurations check with missing subdirectories."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        # Only create providers, missing harnesses and variants
        (configs_dir / "providers").mkdir()

        result = health_service.check_configurations(str(configs_dir))

        assert result.status == HealthStatus.DEGRADED
        assert "Missing" in result.message

    def test_check_configurations_no_providers(self, health_service, tmp_path):
        """Test configurations check with no providers."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        (configs_dir / "providers").mkdir()
        (configs_dir / "harnesses").mkdir()
        (configs_dir / "variants").mkdir()
        # Don't add any config files

        result = health_service.check_configurations(str(configs_dir))

        assert result.status == HealthStatus.DEGRADED
        assert "No provider configurations" in result.message

    def test_run_health_checks_all_healthy(self, health_service, temp_configs_dir, tmp_path):
        """Test running all health checks when all are healthy."""
        # Mock database to use SQLite
        db_path = tmp_path / "test.db"

        with patch.dict(os.environ, {"DATABASE_URL": f"sqlite:///{db_path}"}):
            # Mock HTTP services
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"status": "healthy"}

            with patch("requests.get", return_value=mock_response):
                report = health_service.run_health_checks(temp_configs_dir)

        assert report.status == HealthStatus.HEALTHY
        assert report.is_healthy()
        assert len(report.checks) == 4
        assert all(c.status == HealthStatus.HEALTHY for c in report.checks)

    def test_run_health_checks_with_unhealthy(self, health_service, temp_configs_dir, tmp_path):
        """Test running health checks with some unhealthy."""
        # Mock database to use SQLite
        db_path = tmp_path / "test.db"

        import requests

        with (
            patch.dict(os.environ, {"DATABASE_URL": f"sqlite:///{db_path}"}),
            patch("requests.get", side_effect=requests.exceptions.ConnectionError()),
        ):
            report = health_service.run_health_checks(temp_configs_dir)

        assert report.status == HealthStatus.UNHEALTHY
        assert not report.is_healthy()
        assert len(report.get_unhealthy_checks()) == 2  # LiteLLM and Prometheus

    def test_mask_url(self, health_service):
        """Test URL masking for passwords."""
        url = "postgresql://user:secret@host:5432/db"
        masked = health_service._mask_url(url)

        assert "secret" not in masked
        assert "****" in masked
        assert "user" in masked
        assert "host" in masked


class TestHealthReport:
    """Tests for HealthReport class."""

    def test_is_healthy(self):
        """Test is_healthy method."""
        from benchmark_core.services.health_service import HealthCheckResult

        healthy_check = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            message="OK",
        )
        unhealthy_check = HealthCheckResult(
            name="test2",
            status=HealthStatus.UNHEALTHY,
            message="Failed",
        )

        healthy_report = HealthReport(
            status=HealthStatus.HEALTHY,
            checks=[healthy_check],
            summary="All healthy",
        )
        assert healthy_report.is_healthy()

        unhealthy_report = HealthReport(
            status=HealthStatus.UNHEALTHY,
            checks=[unhealthy_check],
            summary="Unhealthy",
        )
        assert not unhealthy_report.is_healthy()

    def test_get_unhealthy_checks(self):
        """Test get_unhealthy_checks method."""
        from benchmark_core.services.health_service import HealthCheckResult

        healthy_check = HealthCheckResult(
            name="healthy",
            status=HealthStatus.HEALTHY,
            message="OK",
        )
        unhealthy_check = HealthCheckResult(
            name="unhealthy",
            status=HealthStatus.UNHEALTHY,
            message="Failed",
        )

        report = HealthReport(
            status=HealthStatus.UNHEALTHY,
            checks=[healthy_check, unhealthy_check],
            summary="Mixed",
        )

        unhealthy = report.get_unhealthy_checks()
        assert len(unhealthy) == 1
        assert unhealthy[0].name == "unhealthy"
