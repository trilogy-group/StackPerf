"""Collector validation smoke tests for CI.

Validates collector implementations are properly structured and importable.
This ensures collector regressions are caught automatically.
"""

from pathlib import Path

import pytest

# Late imports tested separately
from collectors.litellm_collector import CollectionDiagnostics, LiteLLMCollector
from collectors.prometheus_collector import PrometheusCollector


class TestCollectorStructure:
    """Test collector module structure."""

    def test_collectors_directory_exists(self) -> None:
        """Verify collectors directory exists."""
        collectors_dir = Path(__file__).parent.parent.parent / "src" / "collectors"
        assert collectors_dir.exists(), f"Collectors directory not found: {collectors_dir}"

    def test_collectors_init_exists(self) -> None:
        """Verify collectors __init__.py exists."""
        init_file = Path(__file__).parent.parent.parent / "src" / "collectors" / "__init__.py"
        assert init_file.exists(), f"Collectors __init__.py not found: {init_file}"


class TestCollectorImports:
    """Test that all collector modules can be imported."""

    def test_import_litellm_collector(self) -> None:
        """Test importing litellm_collector module."""
        try:
            from collectors import litellm_collector

            assert litellm_collector is not None
        except ImportError as e:
            pytest.fail(f"Failed to import litellm_collector: {e}")

    def test_import_prometheus_collector(self) -> None:
        """Test importing prometheus_collector module."""
        try:
            from collectors import prometheus_collector

            assert prometheus_collector is not None
        except ImportError as e:
            pytest.fail(f"Failed to import prometheus_collector: {e}")

    def test_import_normalization(self) -> None:
        """Test importing normalization module."""
        try:
            from collectors import normalization

            assert normalization is not None
        except ImportError as e:
            pytest.fail(f"Failed to import normalization: {e}")

    def test_import_normalize_requests(self) -> None:
        """Test importing normalize_requests module."""
        try:
            from collectors import normalize_requests

            assert normalize_requests is not None
        except ImportError as e:
            pytest.fail(f"Failed to import normalize_requests: {e}")

    def test_import_metric_catalog(self) -> None:
        """Test importing metric_catalog module."""
        try:
            from collectors import metric_catalog

            assert metric_catalog is not None
        except ImportError as e:
            pytest.fail(f"Failed to import metric_catalog: {e}")

    def test_import_rollup_job(self) -> None:
        """Test importing rollup_job module."""
        try:
            from collectors import rollup_job

            assert rollup_job is not None
        except ImportError as e:
            pytest.fail(f"Failed to import rollup_job: {e}")

    def test_import_retention_cleanup(self) -> None:
        """Test importing retention_cleanup module."""
        try:
            from collectors import retention_cleanup

            assert retention_cleanup is not None
        except ImportError as e:
            pytest.fail(f"Failed to import retention_cleanup: {e}")


class TestCollectorClassStructure:
    """Test that collector classes have expected structure and methods."""

    def test_litellm_collector_has_required_attributes(self) -> None:
        """Test LiteLLMCollector has expected constructor parameters."""
        # Verify the class can be inspected for init parameters
        import inspect
        sig = inspect.signature(LiteLLMCollector.__init__)
        params = list(sig.parameters.keys())
        assert 'self' in params, "LiteLLMCollector missing self parameter"
        assert 'repository' in params, "LiteLLMCollector missing repository parameter"
        assert 'api_key' in params, "LiteLLMCollector missing api_key parameter"

    def test_litellm_collector_collection_diagnostics_structure(self) -> None:
        """Test CollectionDiagnostics has expected fields."""
        import dataclasses
        assert dataclasses.is_dataclass(CollectionDiagnostics), "CollectionDiagnostics should be a dataclass"
        fields = {f.name for f in dataclasses.fields(CollectionDiagnostics)}
        # Verify actual field names from the implementation
        assert 'total_raw_records' in fields, "CollectionDiagnostics missing total_raw_records"
        assert 'errors' in fields, "CollectionDiagnostics missing errors"
        assert 'normalized_count' in fields, "CollectionDiagnostics missing normalized_count"

    def test_prometheus_collector_has_required_attributes(self) -> None:
        """Test PrometheusCollector has expected constructor parameters."""
        import inspect
        sig = inspect.signature(PrometheusCollector.__init__)
        params = list(sig.parameters.keys())
        assert 'self' in params, "PrometheusCollector missing self parameter"
        # PrometheusCollector uses different parameter names
        assert 'base_url' in params, "PrometheusCollector missing base_url parameter"
        assert 'session_id' in params, "PrometheusCollector missing session_id parameter"


class TestCollectorModuleDocstrings:
    """Test that collector modules have proper documentation."""

    def test_litellm_collector_has_docstring(self) -> None:
        """Test litellm_collector module has docstring."""
        from collectors import litellm_collector

        assert litellm_collector.__doc__ is not None
        assert len(litellm_collector.__doc__) > 0

    def test_prometheus_collector_has_docstring(self) -> None:
        """Test prometheus_collector module has docstring."""
        from collectors import prometheus_collector

        assert prometheus_collector.__doc__ is not None
        assert len(prometheus_collector.__doc__) > 0

    def test_normalization_has_docstring(self) -> None:
        """Test normalization module has docstring."""
        from collectors import normalization

        assert normalization.__doc__ is not None
        assert len(normalization.__doc__) > 0
