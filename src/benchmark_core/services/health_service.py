"""Health check service for verifying stack readiness before session launch."""

import enum
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from benchmark_core.db.session import create_database_engine, get_database_url


class HealthStatus(str, enum.Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: HealthStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    suggestion: str | None = None


@dataclass
class HealthReport:
    """Complete health check report for the stack."""

    status: HealthStatus
    checks: list[HealthCheckResult]
    summary: str

    def is_healthy(self) -> bool:
        """Return True if all checks are healthy."""
        return self.status == HealthStatus.HEALTHY

    def get_unhealthy_checks(self) -> list[HealthCheckResult]:
        """Return list of unhealthy checks."""
        return [c for c in self.checks if c.status == HealthStatus.UNHEALTHY]


class HealthService:
    """Service for verifying stack health before launching benchmark sessions.

    This service performs comprehensive health checks on:
    - Database connectivity
    - LiteLLM proxy health
    - Prometheus metrics endpoint
    - Configuration validity

    The goal is to surface obvious misconfigurations before benchmark traffic starts.
    """

    def __init__(
        self,
        db_session: Session | None = None,
        litellm_base_url: str | None = None,
        litellm_api_key: str | None = None,
        prometheus_url: str | None = None,
    ) -> None:
        """Initialize health service.

        Args:
            db_session: Optional database session. If not provided, creates one.
            litellm_base_url: Optional LiteLLM proxy URL (default: http://localhost:4000).
            litellm_api_key: Optional LiteLLM API key.
            prometheus_url: Optional Prometheus URL (default: http://localhost:9090).
        """
        import os

        self._db_session = db_session
        self._litellm_base_url = litellm_base_url or os.getenv(
            "LITELLM_BASE_URL", "http://localhost:4000"
        )
        self._litellm_api_key = litellm_api_key or os.getenv("LITELLM_MASTER_KEY")
        self._prometheus_url = prometheus_url or os.getenv(
            "PROMETHEUS_URL", "http://localhost:9090"
        )

    def check_database(self) -> HealthCheckResult:
        """Check database connectivity.

        Returns:
            HealthCheckResult with database connection status.
        """
        try:
            database_url = get_database_url()

            # Create engine and test connection
            engine = create_database_engine(database_url)

            with engine.connect() as conn:
                # Execute simple query to verify connection
                result = conn.execute(text("SELECT 1"))
                result.fetchone()

            # Determine database type
            db_type = "PostgreSQL" if "postgresql" in database_url.lower() else "SQLite"

            return HealthCheckResult(
                name="database",
                status=HealthStatus.HEALTHY,
                message=f"{db_type} database connection successful",
                details={"database_type": db_type, "url": self._mask_url(database_url)},
            )

        except Exception as e:
            return HealthCheckResult(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database connection failed: {e}",
                suggestion="Check DATABASE_URL environment variable and ensure database is running",
            )

    def check_litellm_proxy(self) -> HealthCheckResult:
        """Check LiteLLM proxy health endpoint.

        Returns:
            HealthCheckResult with LiteLLM proxy status.
        """
        try:
            import requests

            health_url = f"{self._litellm_base_url}/health/liveliness"

            response = requests.get(health_url, timeout=5)

            if response.status_code == 200:
                data = response.json() if response.headers.get("content-type", "").startswith(
                    "application/json"
                ) else {}

                return HealthCheckResult(
                    name="litellm_proxy",
                    status=HealthStatus.HEALTHY,
                    message="LiteLLM proxy is healthy",
                    details={
                        "url": self._litellm_base_url,
                        "health_endpoint": health_url,
                        "response": data,
                    },
                )
            else:
                return HealthCheckResult(
                    name="litellm_proxy",
                    status=HealthStatus.UNHEALTHY,
                    message=f"LiteLLM proxy returned status {response.status_code}",
                    details={"url": self._litellm_base_url, "status_code": response.status_code},
                    suggestion="Check if LiteLLM container is running with 'docker ps'",
                )

        except requests.exceptions.ConnectionError:
            return HealthCheckResult(
                name="litellm_proxy",
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot connect to LiteLLM proxy at {self._litellm_base_url}",
                suggestion="Start LiteLLM proxy with 'docker-compose up -d litellm'",
            )
        except requests.exceptions.Timeout:
            return HealthCheckResult(
                name="litellm_proxy",
                status=HealthStatus.UNHEALTHY,
                message="LiteLLM proxy health check timed out",
                suggestion="LiteLLM proxy may be overloaded or starting up",
            )
        except ImportError:
            return HealthCheckResult(
                name="litellm_proxy",
                status=HealthStatus.UNHEALTHY,
                message="requests library not available",
                suggestion="Install requests: pip install requests",
            )
        except Exception as e:
            return HealthCheckResult(
                name="litellm_proxy",
                status=HealthStatus.UNHEALTHY,
                message=f"LiteLLM proxy health check failed: {e}",
                suggestion="Check LiteLLM logs with 'docker logs litellm'",
            )

    def check_prometheus(self) -> HealthCheckResult:
        """Check Prometheus metrics endpoint.

        Returns:
            HealthCheckResult with Prometheus status.
        """
        try:
            import requests

            health_url = f"{self._prometheus_url}/-/healthy"

            response = requests.get(health_url, timeout=5)

            if response.status_code == 200:
                return HealthCheckResult(
                    name="prometheus",
                    status=HealthStatus.HEALTHY,
                    message="Prometheus is healthy",
                    details={"url": self._prometheus_url, "health_endpoint": health_url},
                )
            else:
                return HealthCheckResult(
                    name="prometheus",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Prometheus returned status {response.status_code}",
                    details={"url": self._prometheus_url, "status_code": response.status_code},
                    suggestion="Check Prometheus logs with 'docker logs litellm-prometheus'",
                )

        except requests.exceptions.ConnectionError:
            return HealthCheckResult(
                name="prometheus",
                status=HealthStatus.UNHEALTHY,
                message=f"Cannot connect to Prometheus at {self._prometheus_url}",
                suggestion="Start Prometheus with 'docker-compose up -d prometheus'",
            )
        except requests.exceptions.Timeout:
            return HealthCheckResult(
                name="prometheus",
                status=HealthStatus.UNHEALTHY,
                message="Prometheus health check timed out",
                suggestion="Prometheus may be overloaded",
            )
        except ImportError:
            return HealthCheckResult(
                name="prometheus",
                status=HealthStatus.UNHEALTHY,
                message="requests library not available",
                suggestion="Install requests: pip install requests",
            )
        except Exception as e:
            return HealthCheckResult(
                name="prometheus",
                status=HealthStatus.UNHEALTHY,
                message=f"Prometheus health check failed: {e}",
                suggestion="Check Prometheus logs with 'docker logs litellm-prometheus'",
            )

    def check_configurations(self, configs_dir: str = "./configs") -> HealthCheckResult:
        """Check if required configuration files exist.

        Args:
            configs_dir: Path to configuration directory.

        Returns:
            HealthCheckResult with configuration status.
        """
        from pathlib import Path

        config_path = Path(configs_dir)

        if not config_path.exists():
            return HealthCheckResult(
                name="configurations",
                status=HealthStatus.UNHEALTHY,
                message=f"Configuration directory not found: {configs_dir}",
                suggestion=f"Create configuration directory at {configs_dir}",
            )

        # Check for required subdirectories
        required_dirs = ["providers", "harnesses", "variants"]
        missing_dirs = []

        for subdir in required_dirs:
            if not (config_path / subdir).exists():
                missing_dirs.append(subdir)

        # Count configuration files
        config_counts = {}
        for subdir in required_dirs:
            subdir_path = config_path / subdir
            if subdir_path.exists():
                yaml_files = list(subdir_path.glob("*.yaml")) + list(subdir_path.glob("*.yml"))
                config_counts[subdir] = len(yaml_files)
            else:
                config_counts[subdir] = 0

        if missing_dirs:
            return HealthCheckResult(
                name="configurations",
                status=HealthStatus.DEGRADED,
                message=f"Missing configuration directories: {', '.join(missing_dirs)}",
                details=config_counts,
                suggestion=f"Create missing directories under {configs_dir}",
            )

        # Check if we have at least one provider and one variant
        if config_counts.get("providers", 0) == 0:
            return HealthCheckResult(
                name="configurations",
                status=HealthStatus.DEGRADED,
                message="No provider configurations found",
                details=config_counts,
                suggestion="Add at least one provider configuration file in configs/providers/",
            )

        if config_counts.get("variants", 0) == 0:
            return HealthCheckResult(
                name="configurations",
                status=HealthStatus.DEGRADED,
                message="No variant configurations found",
                details=config_counts,
                suggestion="Add at least one variant configuration file in configs/variants/",
            )

        return HealthCheckResult(
            name="configurations",
            status=HealthStatus.HEALTHY,
            message="Configuration files found",
            details=config_counts,
        )

    def run_health_checks(self, configs_dir: str = "./configs") -> HealthReport:
        """Run all health checks and return comprehensive report.

        Args:
            configs_dir: Path to configuration directory.

        Returns:
            HealthReport with overall status and individual check results.
        """
        checks = [
            self.check_database(),
            self.check_litellm_proxy(),
            self.check_prometheus(),
            self.check_configurations(configs_dir),
        ]

        # Determine overall status
        unhealthy = [c for c in checks if c.status == HealthStatus.UNHEALTHY]
        degraded = [c for c in checks if c.status == HealthStatus.DEGRADED]

        if unhealthy:
            overall_status = HealthStatus.UNHEALTHY
            summary = f"{len(unhealthy)} check(s) unhealthy: {', '.join(c.name for c in unhealthy)}"
        elif degraded:
            overall_status = HealthStatus.DEGRADED
            summary = f"{len(degraded)} check(s) degraded: {', '.join(c.name for c in degraded)}"
        else:
            overall_status = HealthStatus.HEALTHY
            summary = "All checks healthy"

        return HealthReport(status=overall_status, checks=checks, summary=summary)

    @staticmethod
    def _mask_url(url: str) -> str:
        """Mask sensitive parts of URL for logging.

        Args:
            url: Database URL to mask.

        Returns:
            URL with password masked.
        """
        import re

        # Mask password in URL if present
        # postgresql://user:password@host/db -> postgresql://user:****@host/db
        return re.sub(r"(://[^:]+:)([^@]+)(@)", r"\1****\3", url)
