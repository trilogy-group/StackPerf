"""Diagnostics service for detailed environment and configuration analysis."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from benchmark_core.db.session import create_database_engine, get_database_url


@dataclass
class DiagnosticResult:
    """Result of a diagnostic check."""

    category: str
    name: str
    status: str  # "ok", "warning", "error"
    value: Any
    message: str | None = None
    suggestion: str | None = None


@dataclass
class DiagnosticsReport:
    """Complete diagnostics report."""

    environment: list[DiagnosticResult]
    configuration: list[DiagnosticResult]
    services: list[DiagnosticResult]

    def has_errors(self) -> bool:
        """Return True if any diagnostic has error status."""
        all_diagnostics = self.environment + self.configuration + self.services
        return any(d.status == "error" for d in all_diagnostics)

    def get_errors(self) -> list[DiagnosticResult]:
        """Return all diagnostics with error status."""
        all_diagnostics = self.environment + self.configuration + self.services
        return [d for d in all_diagnostics if d.status == "error"]

    def get_warnings(self) -> list[DiagnosticResult]:
        """Return all diagnostics with warning status."""
        all_diagnostics = self.environment + self.configuration + self.services
        return [d for d in all_diagnostics if d.status == "warning"]


class DiagnosticsService:
    """Service for comprehensive environment and configuration diagnostics.

    This service provides detailed diagnostics to help operators identify
    and resolve configuration issues before launching benchmark sessions.

    Categories of diagnostics:
    - Environment: env vars, paths, permissions
    - Configuration: providers, harnesses, variants, experiments
    - Services: database, proxy, metrics
    """

    def __init__(
        self,
        db_session: Session | None = None,
        configs_dir: str = "./configs",
    ) -> None:
        """Initialize diagnostics service.

        Args:
            db_session: Optional database session.
            configs_dir: Path to configuration directory.
        """
        self._db_session = db_session
        self._configs_dir = configs_dir

    def diagnose_environment(self) -> list[DiagnosticResult]:
        """Diagnose environment configuration.

        Returns:
            List of environment diagnostic results.
        """
        diagnostics = []

        # Check database URL
        db_url = os.getenv("DATABASE_URL") or os.getenv("BENCHMARK_DATABASE_URL")
        if db_url:
            diagnostics.append(
                DiagnosticResult(
                    category="environment",
                    name="DATABASE_URL",
                    status="ok",
                    value=self._mask_url(db_url),
                    message="Database URL configured",
                )
            )
        else:
            diagnostics.append(
                DiagnosticResult(
                    category="environment",
                    name="DATABASE_URL",
                    status="warning",
                    value=None,
                    message="Using default SQLite database (./benchmark.db)",
                    suggestion="Set DATABASE_URL for production deployments",
                )
            )

        # Check LiteLLM configuration
        litellm_master_key = os.getenv("LITELLM_MASTER_KEY")
        if litellm_master_key:
            diagnostics.append(
                DiagnosticResult(
                    category="environment",
                    name="LITELLM_MASTER_KEY",
                    status="ok",
                    value=f"{litellm_master_key[:6]}..." if len(litellm_master_key) > 6 else "****",
                    message="LiteLLM master key configured",
                )
            )
        else:
            diagnostics.append(
                DiagnosticResult(
                    category="environment",
                    name="LITELLM_MASTER_KEY",
                    status="warning",
                    value=None,
                    message="LITELLM_MASTER_KEY not set",
                    suggestion="Set LITELLM_MASTER_KEY for proxy authentication",
                )
            )

        # Check LiteLLM base URL
        litellm_base_url = os.getenv("LITELLM_BASE_URL", "http://localhost:4000")
        diagnostics.append(
            DiagnosticResult(
                category="environment",
                name="LITELLM_BASE_URL",
                status="ok",
                value=litellm_base_url,
                message="LiteLLM proxy URL",
            )
        )

        # Check Prometheus URL
        prometheus_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")
        diagnostics.append(
            DiagnosticResult(
                category="environment",
                name="PROMETHEUS_URL",
                status="ok",
                value=prometheus_url,
                message="Prometheus metrics URL",
            )
        )

        # Check configs directory
        configs_path = Path(self._configs_dir)
        if configs_path.exists():
            diagnostics.append(
                DiagnosticResult(
                    category="environment",
                    name="CONFIGS_DIR",
                    status="ok",
                    value=str(configs_path.absolute()),
                    message=f"Configuration directory exists at {configs_path.absolute()}",
                )
            )
        else:
            diagnostics.append(
                DiagnosticResult(
                    category="environment",
                    name="CONFIGS_DIR",
                    status="error",
                    value=str(configs_path.absolute()),
                    message=f"Configuration directory not found: {configs_path}",
                    suggestion=f"Create configuration directory at {configs_path.absolute()}",
                )
            )

        # Check write permissions for configs directory
        if configs_path.exists():
            if os.access(configs_path, os.W_OK):
                diagnostics.append(
                    DiagnosticResult(
                        category="environment",
                        name="CONFIGS_DIR_WRITE",
                        status="ok",
                        value="writable",
                        message="Write access to configuration directory",
                    )
                )
            else:
                diagnostics.append(
                    DiagnosticResult(
                        category="environment",
                        name="CONFIGS_DIR_WRITE",
                        status="warning",
                        value="read-only",
                        message="No write access to configuration directory",
                        suggestion="Check permissions if you need to create new configs",
                    )
                )

        return diagnostics

    def diagnose_configuration(self) -> list[DiagnosticResult]:
        """Diagnose configuration files.

        Returns:
            List of configuration diagnostic results.
        """
        diagnostics = []
        configs_path = Path(self._configs_dir)

        # Check providers
        providers = self._count_config_files(configs_path / "providers")
        diagnostics.append(
            DiagnosticResult(
                category="configuration",
                name="providers",
                status="ok" if providers > 0 else "warning",
                value=providers,
                message=f"{providers} provider configuration(s) found",
                suggestion="Add provider configs in configs/providers/" if providers == 0 else None,
            )
        )

        # Check harnesses
        harnesses = self._count_config_files(configs_path / "harnesses")
        diagnostics.append(
            DiagnosticResult(
                category="configuration",
                name="harnesses",
                status="ok" if harnesses > 0 else "warning",
                value=harnesses,
                message=f"{harnesses} harness configuration(s) found",
                suggestion="Add harness configs in configs/harnesses/" if harnesses == 0 else None,
            )
        )

        # Check variants
        variants = self._count_config_files(configs_path / "variants")
        diagnostics.append(
            DiagnosticResult(
                category="configuration",
                name="variants",
                status="ok" if variants > 0 else "warning",
                value=variants,
                message=f"{variants} variant configuration(s) found",
                suggestion="Add variant configs in configs/variants/" if variants == 0 else None,
            )
        )

        # Check experiments
        experiments = self._count_config_files(configs_path / "experiments")
        diagnostics.append(
            DiagnosticResult(
                category="configuration",
                name="experiments",
                status="ok",
                value=experiments,
                message=f"{experiments} experiment configuration(s) found",
            )
        )

        # Check task cards
        task_cards = self._count_config_files(configs_path / "task-cards")
        diagnostics.append(
            DiagnosticResult(
                category="configuration",
                name="task_cards",
                status="ok",
                value=task_cards,
                message=f"{task_cards} task card configuration(s) found",
            )
        )

        # Validate provider config files
        provider_path = configs_path / "providers"
        if provider_path.exists():
            for yaml_file in provider_path.glob("*.yaml"):
                try:
                    result = self._validate_yaml_file(yaml_file)
                    if result:
                        diagnostics.append(result)
                except Exception as e:
                    diagnostics.append(
                        DiagnosticResult(
                            category="configuration",
                            name=f"provider:{yaml_file.name}",
                            status="error",
                            value=None,
                            message=f"Failed to validate {yaml_file}: {e}",
                        )
                    )

        return diagnostics

    def diagnose_services(self) -> list[DiagnosticResult]:
        """Diagnose service connectivity and status.

        Returns:
            List of service diagnostic results.
        """
        diagnostics = []

        # Database diagnostics
        db_diag = self._diagnose_database()
        diagnostics.append(db_diag)

        # LiteLLM proxy diagnostics
        litellm_diag = self._diagnose_litellm()
        diagnostics.append(litellm_diag)

        # Prometheus diagnostics
        prom_diag = self._diagnose_prometheus()
        diagnostics.append(prom_diag)

        return diagnostics

    def run_diagnostics(self) -> DiagnosticsReport:
        """Run all diagnostics and return comprehensive report.

        Returns:
            DiagnosticsReport with all diagnostic categories.
        """
        return DiagnosticsReport(
            environment=self.diagnose_environment(),
            configuration=self.diagnose_configuration(),
            services=self.diagnose_services(),
        )

    def _count_config_files(self, directory: Path) -> int:
        """Count YAML configuration files in a directory.

        Args:
            directory: Path to configuration directory.

        Returns:
            Number of YAML files found.
        """
        if not directory.exists():
            return 0
        yaml_files = list(directory.glob("*.yaml")) + list(directory.glob("*.yml"))
        return len(yaml_files)

    def _validate_yaml_file(self, yaml_file: Path) -> DiagnosticResult | None:
        """Validate a YAML configuration file.

        Args:
            yaml_file: Path to YAML file.

        Returns:
            DiagnosticResult if validation fails, None otherwise.
        """
        try:
            import yaml

            with open(yaml_file) as f:
                config = yaml.safe_load(f)

            # Basic validation for provider configs
            if "providers" in str(yaml_file):
                required_fields = ["name"]
                missing = [f for f in required_fields if f not in config]
                if missing:
                    return DiagnosticResult(
                        category="configuration",
                        name=f"provider:{yaml_file.name}",
                        status="warning",
                        value=missing,
                        message=f"Missing required fields: {', '.join(missing)}",
                        suggestion=f"Add missing fields to {yaml_file}",
                    )

            return None

        except ImportError:
            return DiagnosticResult(
                category="configuration",
                name=f"provider:{yaml_file.name}",
                status="warning",
                value=None,
                message="PyYAML not available for validation",
                suggestion="Install PyYAML: pip install pyyaml",
            )
        except Exception as e:
            return DiagnosticResult(
                category="configuration",
                name=f"provider:{yaml_file.name}",
                status="error",
                value=None,
                message=f"YAML parsing error: {e}",
                suggestion=f"Fix YAML syntax in {yaml_file}",
            )

    def _diagnose_database(self) -> DiagnosticResult:
        """Diagnose database connectivity and status.

        Returns:
            DiagnosticResult with database status.
        """
        try:
            database_url = get_database_url()
            engine = create_database_engine(database_url)

            with engine.connect() as conn:
                # Get database version
                if "postgresql" in database_url.lower():
                    result = conn.execute(text("SELECT version()"))
                    row = result.fetchone()
                    version = row[0] if row else "unknown"
                    db_type = "PostgreSQL"
                else:
                    version = "SQLite"
                    db_type = "SQLite"

                # Get table count
                result = conn.execute(
                    text(
                        "SELECT count(*) FROM sqlite_master WHERE type='table'"
                        if "sqlite" in database_url.lower()
                        else "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'"
                    )
                )
                row = result.fetchone()
                table_count = row[0] if row else 0

            return DiagnosticResult(
                category="services",
                name="database",
                status="ok",
                value={"type": db_type, "version": version.split(",")[0], "tables": table_count},
                message=f"{db_type} connected, {table_count} tables",
            )

        except Exception as e:
            return DiagnosticResult(
                category="services",
                name="database",
                status="error",
                value=None,
                message=f"Database connection failed: {e}",
                suggestion="Check DATABASE_URL and ensure database is running",
            )

    def _diagnose_litellm(self) -> DiagnosticResult:
        """Diagnose LiteLLM proxy connectivity and status.

        Returns:
            DiagnosticResult with LiteLLM status.
        """
        try:
            import requests  # type: ignore[import-untyped]

            base_url = os.getenv("LITELLM_BASE_URL", "http://localhost:4000")
            api_key = os.getenv("LITELLM_MASTER_KEY")

            # Check health endpoint
            health_url = f"{base_url}/health/liveliness"
            response = requests.get(health_url, timeout=5)

            if response.status_code != 200:
                return DiagnosticResult(
                    category="services",
                    name="litellm_proxy",
                    status="error",
                    value={"url": base_url, "status_code": response.status_code},
                    message=f"LiteLLM proxy unhealthy: status {response.status_code}",
                    suggestion="Check LiteLLM logs: docker logs litellm",
                )

            # Try to get model list if API key is available
            models = []
            if api_key:
                try:
                    models_url = f"{base_url}/v1/models"
                    headers = {"Authorization": f"Bearer {api_key}"}
                    models_response = requests.get(models_url, headers=headers, timeout=5)
                    if models_response.status_code == 200:
                        models_data = models_response.json()
                        models = [m.get("id", m.get("model")) for m in models_data.get("data", [])]
                except Exception:
                    pass  # Non-critical if we can't get model list

            return DiagnosticResult(
                category="services",
                name="litellm_proxy",
                status="ok",
                value={"url": base_url, "models_count": len(models), "models": models[:5]},
                message=f"LiteLLM proxy healthy, {len(models)} model(s) configured",
            )

        except ImportError:
            return DiagnosticResult(
                category="services",
                name="litellm_proxy",
                status="error",
                value=None,
                message="requests library not available",
                suggestion="Install requests: pip install requests",
            )
        except requests.exceptions.ConnectionError:
            return DiagnosticResult(
                category="services",
                name="litellm_proxy",
                status="error",
                value={"url": os.getenv("LITELLM_BASE_URL", "http://localhost:4000")},
                message="Cannot connect to LiteLLM proxy",
                suggestion="Start LiteLLM: docker-compose up -d litellm",
            )
        except Exception as e:
            return DiagnosticResult(
                category="services",
                name="litellm_proxy",
                status="error",
                value=None,
                message=f"LiteLLM diagnostics failed: {e}",
                suggestion="Check LiteLLM logs: docker logs litellm",
            )

    def _diagnose_prometheus(self) -> DiagnosticResult:
        """Diagnose Prometheus connectivity and status.

        Returns:
            DiagnosticResult with Prometheus status.
        """
        try:
            import requests

            base_url = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

            # Check health endpoint
            health_url = f"{base_url}/-/healthy"
            response = requests.get(health_url, timeout=5)

            if response.status_code != 200:
                return DiagnosticResult(
                    category="services",
                    name="prometheus",
                    status="error",
                    value={"url": base_url, "status_code": response.status_code},
                    message=f"Prometheus unhealthy: status {response.status_code}",
                    suggestion="Check Prometheus logs: docker logs litellm-prometheus",
                )

            # Try to get scrape targets
            targets = []
            try:
                targets_url = f"{base_url}/api/v1/targets"
                targets_response = requests.get(targets_url, timeout=5)
                if targets_response.status_code == 200:
                    targets_data = targets_response.json()
                    targets = [
                        t.get("labels", {}).get("job", "unknown")
                        for t in targets_data.get("data", {}).get("activeTargets", [])
                    ]
            except Exception:
                pass  # Non-critical if we can't get targets

            return DiagnosticResult(
                category="services",
                name="prometheus",
                status="ok",
                value={"url": base_url, "targets": targets[:5]},
                message=f"Prometheus healthy, {len(targets)} target(s) configured",
            )

        except ImportError:
            return DiagnosticResult(
                category="services",
                name="prometheus",
                status="error",
                value=None,
                message="requests library not available",
                suggestion="Install requests: pip install requests",
            )
        except requests.exceptions.ConnectionError:
            return DiagnosticResult(
                category="services",
                name="prometheus",
                status="error",
                value={"url": os.getenv("PROMETHEUS_URL", "http://localhost:9090")},
                message="Cannot connect to Prometheus",
                suggestion="Start Prometheus: docker-compose up -d prometheus",
            )
        except Exception as e:
            return DiagnosticResult(
                category="services",
                name="prometheus",
                status="error",
                value=None,
                message=f"Prometheus diagnostics failed: {e}",
                suggestion="Check Prometheus logs: docker logs litellm-prometheus",
            )

    @staticmethod
    def _mask_url(url: str) -> str:
        """Mask sensitive parts of URL for logging.

        Args:
            url: URL to mask.

        Returns:
            URL with password masked.
        """
        import re

        # Mask password in URL if present
        return re.sub(r"(://[^:]+:)([^@]+)(@)", r"\1****\3", url)
