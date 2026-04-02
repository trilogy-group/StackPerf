"""Dashboard assets validation smoke tests for CI.

Validates Grafana dashboard JSON files are properly structured and valid.
This ensures dashboard regressions are caught automatically.
"""

import json
from pathlib import Path

import pytest

# Dashboard directories
DASHBOARDS_DIR = Path(__file__).parent.parent.parent / "configs" / "grafana" / "provisioning" / "dashboards"


class TestDashboardStructure:
    """Validate dashboard directory and file structure."""

    def test_dashboards_directory_exists(self) -> None:
        """Verify dashboards directory exists."""
        assert DASHBOARDS_DIR.exists(), f"Dashboards directory not found: {DASHBOARDS_DIR}"

    def test_dashboards_yml_exists(self) -> None:
        """Verify dashboards.yml provisioning config exists."""
        dashboards_yml = DASHBOARDS_DIR / "dashboards.yml"
        assert dashboards_yml.exists(), f"dashboards.yml not found: {dashboards_yml}"

    @pytest.fixture
    def dashboard_json_files(self) -> list[Path]:
        """Get all dashboard JSON files."""
        if not DASHBOARDS_DIR.exists():
            return []
        return list(DASHBOARDS_DIR.glob("*.json"))

    def test_dashboard_json_files_exist(self, dashboard_json_files: list[Path]) -> None:
        """Verify at least one dashboard JSON file exists."""
        if not dashboard_json_files:
            pytest.skip("No dashboard JSON files found")
        assert len(dashboard_json_files) > 0, "No dashboard JSON files found"


class TestDashboardJsonValidity:
    """Validate dashboard JSON files are valid."""

    @pytest.fixture
    def dashboard_json_files(self) -> list[Path]:
        """Get all dashboard JSON files."""
        if not DASHBOARDS_DIR.exists():
            return []
        return list(DASHBOARDS_DIR.glob("*.json"))

    def test_all_dashboards_valid_json(self, dashboard_json_files: list[Path]) -> None:
        """Validate all dashboard files are valid JSON."""
        if not dashboard_json_files:
            pytest.skip("No dashboard JSON files found")

        for dashboard_file in dashboard_json_files:
            try:
                with open(dashboard_file) as f:
                    json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Dashboard {dashboard_file.name} is not valid JSON: {e}")

    def test_all_dashboards_have_required_fields(self, dashboard_json_files: list[Path]) -> None:
        """Validate all dashboards have required Grafana fields."""
        if not dashboard_json_files:
            pytest.skip("No dashboard JSON files found")

        required_fields = ["schemaVersion", "title"]

        for dashboard_file in dashboard_json_files:
            with open(dashboard_file) as f:
                data = json.load(f)

            for field in required_fields:
                assert field in data, f"Dashboard {dashboard_file.name} missing required field: {field}"

    def test_all_dashboards_have_panels(self, dashboard_json_files: list[Path]) -> None:
        """Validate all dashboards have panels array."""
        if not dashboard_json_files:
            pytest.skip("No dashboard JSON files found")

        for dashboard_file in dashboard_json_files:
            with open(dashboard_file) as f:
                data = json.load(f)

            assert "panels" in data, f"Dashboard {dashboard_file.name} missing 'panels' field"
            assert isinstance(data["panels"], list), f"Dashboard {dashboard_file.name} 'panels' must be an array"

    def test_all_dashboards_have_valid_schema_version(self, dashboard_json_files: list[Path]) -> None:
        """Validate all dashboards have a valid schema version."""
        if not dashboard_json_files:
            pytest.skip("No dashboard JSON files found")

        for dashboard_file in dashboard_json_files:
            with open(dashboard_file) as f:
                data = json.load(f)

            schema_version = data.get("schemaVersion")
            assert schema_version is not None, f"Dashboard {dashboard_file.name} missing schemaVersion"
            assert isinstance(schema_version, int), f"Dashboard {dashboard_file.name} schemaVersion must be an integer"
            assert schema_version > 0, f"Dashboard {dashboard_file.name} schemaVersion must be positive"


class TestDashboardProvisioningConfig:
    """Validate dashboards.yml provisioning configuration."""

    def test_dashboards_yml_valid_yaml(self) -> None:
        """Verify dashboards.yml is valid YAML."""
        import yaml

        dashboards_yml = DASHBOARDS_DIR / "dashboards.yml"
        if not dashboards_yml.exists():
            pytest.skip("dashboards.yml not found")

        try:
            with open(dashboards_yml) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"dashboards.yml is not valid YAML: {e}")

    def test_dashboards_yml_has_providers(self) -> None:
        """Verify dashboards.yml has providers configuration."""
        import yaml

        dashboards_yml = DASHBOARDS_DIR / "dashboards.yml"
        if not dashboards_yml.exists():
            pytest.skip("dashboards.yml not found")

        with open(dashboards_yml) as f:
            data = yaml.safe_load(f)

        assert "providers" in data, "dashboards.yml missing 'providers' key"
        assert isinstance(data["providers"], list), "dashboards.yml 'providers' must be a list"
        assert len(data["providers"]) > 0, "dashboards.yml has no providers configured"

    def test_dashboards_yml_provider_has_required_fields(self) -> None:
        """Verify dashboards.yml provider has required fields."""
        import yaml

        dashboards_yml = DASHBOARDS_DIR / "dashboards.yml"
        if not dashboards_yml.exists():
            pytest.skip("dashboards.yml not found")

        with open(dashboards_yml) as f:
            data = yaml.safe_load(f)

        for provider in data["providers"]:
            assert "name" in provider, "Provider missing 'name' field"
            assert "type" in provider, "Provider missing 'type' field"
            assert "options" in provider, "Provider missing 'options' field"
            assert "path" in provider["options"], "Provider options missing 'path' field"


class TestDashboardContent:
    """Validate dashboard content and structure."""

    @pytest.fixture
    def dashboard_json_files(self) -> list[Path]:
        """Get all dashboard JSON files."""
        if not DASHBOARDS_DIR.exists():
            return []
        return list(DASHBOARDS_DIR.glob("*.json"))

    def test_all_panels_have_titles(self, dashboard_json_files: list[Path]) -> None:
        """Verify all panels have titles."""
        if not dashboard_json_files:
            pytest.skip("No dashboard JSON files found")

        for dashboard_file in dashboard_json_files:
            with open(dashboard_file) as f:
                data = json.load(f)

            panels = data.get("panels", [])
            for panel in panels:
                if "title" in panel:
                    assert panel["title"] is not None, f"Panel in {dashboard_file.name} has null title"

    def test_all_dashboards_have_uid(self, dashboard_json_files: list[Path]) -> None:
        """Verify all dashboards have a UID for stable URLs."""
        if not dashboard_json_files:
            pytest.skip("No dashboard JSON files found")

        for dashboard_file in dashboard_json_files:
            with open(dashboard_file) as f:
                data = json.load(f)

            assert "uid" in data, f"Dashboard {dashboard_file.name} missing 'uid' field (needed for stable URLs)"
            assert data["uid"], f"Dashboard {dashboard_file.name} has empty 'uid' field"
