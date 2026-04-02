"""Unit tests for diagnostics service."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from benchmark_core.services.diagnostics_service import (
    DiagnosticResult,
    DiagnosticsReport,
    DiagnosticsService,
)


@pytest.fixture
def diagnostics_service():
    """Create diagnostics service instance."""
    return DiagnosticsService(configs_dir="./configs")


@pytest.fixture
def temp_configs_dir():
    """Create temporary configs directory with files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        configs_path = Path(tmpdir) / "configs"
        configs_path.mkdir()

        # Create required subdirectories
        (configs_path / "providers").mkdir()
        (configs_path / "harnesses").mkdir()
        (configs_path / "variants").mkdir()
        (configs_path / "experiments").mkdir()
        (configs_path / "task-cards").mkdir()

        # Create sample config files
        (configs_path / "providers" / "test.yaml").write_text("name: test\n")
        (configs_path / "harnesses" / "test.yaml").write_text("name: test\n")
        (configs_path / "variants" / "test.yaml").write_text("name: test\n")

        yield str(configs_path)


class TestDiagnosticsService:
    """Tests for DiagnosticsService class."""

    def test_diagnose_environment_database_url_set(self, diagnostics_service):
        """Test environment diagnostics with DATABASE_URL set."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://user:pass@host/db"}):
            diagnostics = diagnostics_service.diagnose_environment()

        db_diag = next(d for d in diagnostics if d.name == "DATABASE_URL")
        assert db_diag.status == "ok"
        assert "configured" in db_diag.message.lower()

    def test_diagnose_environment_database_url_not_set(self, diagnostics_service):
        """Test environment diagnostics without DATABASE_URL."""
        with patch.dict(os.environ, {}, clear=["DATABASE_URL", "BENCHMARK_DATABASE_URL"]):
            diagnostics = diagnostics_service.diagnose_environment()

        db_diag = next(d for d in diagnostics if d.name == "DATABASE_URL")
        assert db_diag.status == "warning"
        assert "SQLite" in db_diag.message

    def test_diagnose_environment_litellm_key_set(self, diagnostics_service):
        """Test environment diagnostics with LITELLM_MASTER_KEY set."""
        with patch.dict(os.environ, {"LITELLM_MASTER_KEY": "sk-test-key-12345"}):
            diagnostics = diagnostics_service.diagnose_environment()

        key_diag = next(d for d in diagnostics if d.name == "LITELLM_MASTER_KEY")
        assert key_diag.status == "ok"
        assert "configured" in key_diag.message.lower()
        assert "sk-tes..." in key_diag.value  # Should be masked (first 6 chars + ...)

    def test_diagnose_environment_litellm_key_not_set(self, diagnostics_service):
        """Test environment diagnostics without LITELLM_MASTER_KEY."""
        with patch.dict(os.environ, {}, clear=["LITELLM_MASTER_KEY"]):
            diagnostics = diagnostics_service.diagnose_environment()

        key_diag = next(d for d in diagnostics if d.name == "LITELLM_MASTER_KEY")
        assert key_diag.status == "warning"
        assert "not set" in key_diag.message.lower()

    def test_diagnose_environment_configs_dir_exists(self, diagnostics_service, temp_configs_dir):
        """Test environment diagnostics with configs directory."""
        service = DiagnosticsService(configs_dir=temp_configs_dir)
        diagnostics = service.diagnose_environment()

        dir_diag = next(d for d in diagnostics if d.name == "CONFIGS_DIR")
        assert dir_diag.status == "ok"
        assert "exists" in dir_diag.message.lower()

    def test_diagnose_environment_configs_dir_not_exists(self, diagnostics_service):
        """Test environment diagnostics with missing configs directory."""
        service = DiagnosticsService(configs_dir="/nonexistent/path")
        diagnostics = service.diagnose_environment()

        dir_diag = next(d for d in diagnostics if d.name == "CONFIGS_DIR")
        assert dir_diag.status == "error"
        assert "not found" in dir_diag.message.lower()

    def test_diagnose_configuration_with_files(self, diagnostics_service, temp_configs_dir):
        """Test configuration diagnostics with config files."""
        service = DiagnosticsService(configs_dir=temp_configs_dir)
        diagnostics = service.diagnose_configuration()

        providers_diag = next(d for d in diagnostics if d.name == "providers")
        assert providers_diag.status == "ok"
        assert providers_diag.value == 1

        harnesses_diag = next(d for d in diagnostics if d.name == "harnesses")
        assert harnesses_diag.status == "ok"

        variants_diag = next(d for d in diagnostics if d.name == "variants")
        assert variants_diag.status == "ok"

    def test_diagnose_configuration_no_providers(self, diagnostics_service, tmp_path):
        """Test configuration diagnostics with no providers."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        (configs_dir / "providers").mkdir()
        (configs_dir / "harnesses").mkdir()
        (configs_dir / "variants").mkdir()

        service = DiagnosticsService(configs_dir=str(configs_dir))
        diagnostics = service.diagnose_configuration()

        providers_diag = next(d for d in diagnostics if d.name == "providers")
        assert providers_diag.status == "warning"
        assert providers_diag.value == 0

    def test_diagnose_services_database_success(self, diagnostics_service, tmp_path):
        """Test database service diagnostics with SQLite."""
        db_path = tmp_path / "test.db"

        with patch.dict(os.environ, {"DATABASE_URL": f"sqlite:///{db_path}"}):
            diag = diagnostics_service._diagnose_database()

        assert diag.status == "ok"
        assert "SQLite" in diag.message

    def test_diagnose_services_database_failure(self, diagnostics_service):
        """Test database service diagnostics with connection failure."""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://invalid:5432/nonexistent"}):
            diag = diagnostics_service._diagnose_database()

        assert diag.status == "error"
        assert "failed" in diag.message.lower()

    def test_diagnose_services_litellm_success(self, diagnostics_service):
        """Test LiteLLM service diagnostics with healthy proxy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_models_response = MagicMock()
        mock_models_response.status_code = 200
        mock_models_response.json.return_value = {
            "data": [{"id": "gpt-4"}, {"model": "gpt-3.5-turbo"}]
        }

        with (
            patch.dict(os.environ, {"LITELLM_MASTER_KEY": "sk-test"}),
            patch("httpx.get", side_effect=[mock_response, mock_models_response]),
        ):
            diag = diagnostics_service._diagnose_litellm()

        assert diag.status == "ok"
        assert "healthy" in diag.message.lower()

    def test_diagnose_services_litellm_connection_error(self, diagnostics_service):
        """Test LiteLLM service diagnostics with connection error."""
        with patch(
            "httpx.get",
            side_effect=httpx.ConnectError(
                "boom",
                request=httpx.Request("GET", "http://localhost:4000/health/liveliness"),
            ),
        ):
            diag = diagnostics_service._diagnose_litellm()

        assert diag.status == "error"
        assert "Cannot connect" in diag.message

    def test_diagnose_services_prometheus_success(self, diagnostics_service):
        """Test Prometheus service diagnostics with healthy service."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_targets_response = MagicMock()
        mock_targets_response.status_code = 200
        mock_targets_response.json.return_value = {
            "data": {"activeTargets": [{"labels": {"job": "litellm"}}]}
        }

        with patch("httpx.get", side_effect=[mock_response, mock_targets_response]):
            diag = diagnostics_service._diagnose_prometheus()

        assert diag.status == "ok"
        assert "healthy" in diag.message.lower()

    def test_diagnose_services_prometheus_connection_error(self, diagnostics_service):
        """Test Prometheus service diagnostics with connection error."""
        with patch(
            "httpx.get",
            side_effect=httpx.ConnectError(
                "boom",
                request=httpx.Request("GET", "http://localhost:9090/-/healthy"),
            ),
        ):
            diag = diagnostics_service._diagnose_prometheus()

        assert diag.status == "error"
        assert "Cannot connect" in diag.message

    def test_run_diagnostics(self, diagnostics_service, temp_configs_dir, tmp_path):
        """Test running all diagnostics."""
        db_path = tmp_path / "test.db"
        service = DiagnosticsService(configs_dir=temp_configs_dir)

        with patch.dict(os.environ, {"DATABASE_URL": f"sqlite:///{db_path}"}):
            # Mock HTTP services
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": []}

            with patch("httpx.get", return_value=mock_response):
                report = service.run_diagnostics()

        assert isinstance(report, DiagnosticsReport)
        assert len(report.environment) > 0
        assert len(report.configuration) > 0
        assert len(report.services) == 3  # database, litellm, prometheus


class TestDiagnosticsReport:
    """Tests for DiagnosticsReport class."""

    def test_has_errors_true(self):
        """Test has_errors with errors present."""
        error_diag = DiagnosticResult(
            category="test",
            name="error_test",
            status="error",
            value=None,
            message="Error",
        )
        ok_diag = DiagnosticResult(
            category="test",
            name="ok_test",
            status="ok",
            value=None,
            message="OK",
        )

        report = DiagnosticsReport(
            environment=[ok_diag],
            configuration=[error_diag],
            services=[ok_diag],
        )

        assert report.has_errors()
        assert len(report.get_errors()) == 1

    def test_has_errors_false(self):
        """Test has_errors with no errors."""
        ok_diag = DiagnosticResult(
            category="test",
            name="ok_test",
            status="ok",
            value=None,
            message="OK",
        )
        warning_diag = DiagnosticResult(
            category="test",
            name="warning_test",
            status="warning",
            value=None,
            message="Warning",
        )

        report = DiagnosticsReport(
            environment=[ok_diag],
            configuration=[warning_diag],
            services=[ok_diag],
        )

        assert not report.has_errors()
        assert len(report.get_errors()) == 0
        assert len(report.get_warnings()) == 1

    def test_get_warnings(self):
        """Test get_warnings method."""
        ok_diag = DiagnosticResult(
            category="test",
            name="ok_test",
            status="ok",
            value=None,
            message="OK",
        )
        warning_diag = DiagnosticResult(
            category="test",
            name="warning_test",
            status="warning",
            value=None,
            message="Warning",
        )

        report = DiagnosticsReport(
            environment=[warning_diag, ok_diag],
            configuration=[],
            services=[],
        )

        warnings = report.get_warnings()
        assert len(warnings) == 1
        assert warnings[0].status == "warning"
