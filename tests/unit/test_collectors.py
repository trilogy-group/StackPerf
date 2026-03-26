"""Unit tests for collectors package."""

from uuid import UUID, uuid4

import pytest

from benchmark_core.models import Request, Session


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
        session_id=UUID("12345678-1234-1234-1234-123456789abc"),
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


def test_import_metric_catalog() -> None:
    """Smoke test: metric catalog imports successfully."""
    from collectors.metric_catalog import MetricCatalog

    catalog = MetricCatalog()
    assert catalog is not None


class TestMetricCatalog:
    """Tests for the MetricCatalog class."""

    def test_get_latency_queries_returns_dict(self) -> None:
        """MetricCatalog returns latency queries as dictionary."""
        from collectors.metric_catalog import MetricCatalog

        catalog = MetricCatalog()
        queries = catalog.get_latency_queries("test-session-123")

        assert isinstance(queries, dict)
        assert "latency_median_ms" in queries
        assert "latency_p95_ms" in queries
        assert "latency_p99_ms" in queries

    def test_latency_queries_contain_session_filter(self) -> None:
        """Latency queries include session_id filter."""
        from collectors.metric_catalog import MetricCatalog

        catalog = MetricCatalog()
        queries = catalog.get_latency_queries("session-abc")

        for query in queries.values():
            assert 'session_id="session-abc"' in query

    def test_get_throughput_query_returns_string(self) -> None:
        """MetricCatalog returns throughput query string."""
        from collectors.metric_catalog import MetricCatalog

        catalog = MetricCatalog()
        query = catalog.get_throughput_query("session-xyz")

        assert isinstance(query, str)
        assert 'session_id="session-xyz"' in query
        assert "rate" in query

    def test_get_error_queries_returns_dict(self) -> None:
        """MetricCatalog returns error queries as dictionary."""
        from collectors.metric_catalog import MetricCatalog

        catalog = MetricCatalog()
        queries = catalog.get_error_queries("session-123")

        assert isinstance(queries, dict)
        assert "error_rate" in queries
        assert "error_percentage" in queries

    def test_get_cache_queries_returns_dict(self) -> None:
        """MetricCatalog returns cache queries as dictionary."""
        from collectors.metric_catalog import MetricCatalog

        catalog = MetricCatalog()
        queries = catalog.get_cache_queries("session-123")

        assert isinstance(queries, dict)
        assert "cache_hit_rate" in queries
        assert "cache_hit_percentage" in queries

    def test_compute_rollup_with_valid_values(self) -> None:
        """compute_rollup returns MetricRollup for valid values."""
        from collectors.metric_catalog import MetricCatalog

        catalog = MetricCatalog()
        values = [100.0, 200.0, 300.0, 400.0, 500.0]

        rollup = catalog.compute_rollup(
            dimension_type="session",
            dimension_id="test-session",
            metric_name="latency_median_ms",
            values=values,
        )

        assert rollup is not None
        assert rollup.dimension_type == "session"
        assert rollup.dimension_id == "test-session"
        assert rollup.metric_name == "latency_median_ms"
        assert rollup.sample_count == 5

    def test_compute_rollup_returns_none_for_empty_values(self) -> None:
        """compute_rollup returns None for empty values (empty window handling)."""
        from collectors.metric_catalog import MetricCatalog

        catalog = MetricCatalog()

        rollup = catalog.compute_rollup(
            dimension_type="session",
            dimension_id="test-session",
            metric_name="latency_median_ms",
            values=[],
        )

        # Empty windows should not corrupt aggregates
        assert rollup is None


class TestRollupJob:
    """Tests for the RollupJob class."""

    @pytest.fixture
    def sample_request(self) -> Request:
        """Create a sample request for testing."""
        return Request(
            request_id="req-001",
            session_id=uuid4(),
            provider="openai",
            model="gpt-4",
            timestamp=1625097600.0,  # type: ignore[arg-type]
            latency_ms=150.0,
            ttft_ms=50.0,
            tokens_prompt=100,
            tokens_completion=50,
            error=False,
            cache_hit=True,
        )

    @pytest.fixture
    def sample_requests(self) -> list[Request]:
        """Create multiple sample requests for testing."""
        base_id = uuid4()
        return [
            Request(
                request_id=f"req-{i:03d}",
                session_id=base_id,
                provider="openai",
                model="gpt-4",
                timestamp=1625097600.0,  # type: ignore[arg-type]
                latency_ms=float(100 + i * 20),  # 100, 120, 140, 160, 180
                ttft_ms=float(40 + i * 5),
                tokens_prompt=100 + i * 10,
                tokens_completion=50 + i * 5,
                error=i == 4,  # Last one has error
                cache_hit=i % 2 == 0,  # Alternating cache hits
            )
            for i in range(5)
        ]

    @pytest.mark.asyncio
    async def test_compute_request_metrics_returns_rollups(
        self,
        sample_request: Request,
    ) -> None:
        """compute_request_metrics returns list of MetricRollup objects."""
        from collectors.rollup_job import RollupJob

        job = RollupJob()
        rollups = await job.compute_request_metrics(sample_request)

        assert isinstance(rollups, list)
        assert len(rollups) > 0

        # Check that expected metrics are present
        metric_names = {r.metric_name for r in rollups}
        assert "latency_ms" in metric_names
        assert "time_to_first_token_ms" in metric_names
        assert "error_flag" in metric_names

    @pytest.mark.asyncio
    async def test_compute_request_metrics_latency_per_token(
        self,
        sample_request: Request,
    ) -> None:
        """compute_request_metrics calculates per-token latency correctly."""
        from collectors.rollup_job import RollupJob

        job = RollupJob()
        rollups = await job.compute_request_metrics(sample_request)

        # Find the per-token latency rollup
        per_token_rollup = next(
            (r for r in rollups if r.metric_name == "latency_per_token_ms"),
            None,
        )

        assert per_token_rollup is not None
        # Expected: 150ms / (100 + 50) tokens = 1.0 ms/token
        assert per_token_rollup.metric_value == 1.0

    @pytest.mark.asyncio
    async def test_compute_session_metrics_median_and_p95(
        self,
        sample_requests: list[Request],
    ) -> None:
        """compute_session_metrics calculates median and p95 correctly.

        This test verifies the acceptance criteria for median and p95 latency.
        """
        from collectors.rollup_job import RollupJob

        job = RollupJob()
        session_id = sample_requests[0].session_id
        rollups = await job.compute_session_metrics(session_id, sample_requests)

        # Find median and p95 rollups
        median_rollup = next(
            (r for r in rollups if r.metric_name == "latency_median_ms"),
            None,
        )
        p95_rollup = next(
            (r for r in rollups if r.metric_name == "latency_p95_ms"),
            None,
        )

        assert median_rollup is not None, "Median rollup should be present"
        assert p95_rollup is not None, "P95 rollup should be present"

        # Values: [100, 120, 140, 160, 180]
        # Median (middle value) = 140
        assert median_rollup.metric_value == 140.0

        # P95 (95th percentile index = int(5 * 0.95) = 4) = 180
        assert p95_rollup.metric_value == 180.0

    @pytest.mark.asyncio
    async def test_compute_session_metrics_empty_requests(
        self,
    ) -> None:
        """compute_session_metrics handles empty windows without corrupting aggregates."""
        from collectors.rollup_job import RollupJob

        job = RollupJob()
        session_id = uuid4()
        rollups = await job.compute_session_metrics(session_id, [])

        # Empty windows should return empty list, not corrupt data
        assert rollups == []

    @pytest.mark.asyncio
    async def test_compute_session_metrics_error_rate(
        self,
        sample_requests: list[Request],
    ) -> None:
        """compute_session_metrics calculates error rate correctly."""
        from collectors.rollup_job import RollupJob

        job = RollupJob()
        session_id = sample_requests[0].session_id
        rollups = await job.compute_session_metrics(session_id, sample_requests)

        error_rollup = next(
            (r for r in rollups if r.metric_name == "error_rate"),
            None,
        )

        assert error_rollup is not None
        # 1 error out of 5 requests = 0.2
        assert error_rollup.metric_value == 0.2
        assert error_rollup.sample_count == 5

    @pytest.mark.asyncio
    async def test_compute_session_metrics_cache_rate(
        self,
        sample_requests: list[Request],
    ) -> None:
        """compute_session_metrics calculates cache hit rate correctly."""
        from collectors.rollup_job import RollupJob

        job = RollupJob()
        session_id = sample_requests[0].session_id
        rollups = await job.compute_session_metrics(session_id, sample_requests)

        cache_rollup = next(
            (r for r in rollups if r.metric_name == "cache_hit_rate"),
            None,
        )

        assert cache_rollup is not None
        # Cache hits at indices 0, 2, 4 = 3 out of 5 = 0.6
        assert cache_rollup.metric_value == 0.6
        assert cache_rollup.sample_count == 5

    @pytest.mark.asyncio
    async def test_compute_variant_metrics_with_sessions(self) -> None:
        """compute_variant_metrics returns metrics for variant with sessions."""
        from collectors.rollup_job import RollupJob

        job = RollupJob()
        sessions = [
            Session(
                experiment_id="exp-001",
                variant_id="variant-a",
                task_card_id="task-001",
                harness_profile="default",
                repo_path="/tmp/test",
                git_branch="main",
                git_commit="abc123",
            ),
            Session(
                experiment_id="exp-001",
                variant_id="variant-a",
                task_card_id="task-001",
                harness_profile="default",
                repo_path="/tmp/test",
                git_branch="main",
                git_commit="abc124",
            ),
        ]

        rollups = await job.compute_variant_metrics("variant-a", sessions)

        assert isinstance(rollups, list)
        assert len(rollups) > 0

        session_count = next(
            (r for r in rollups if r.metric_name == "session_count"),
            None,
        )
        assert session_count is not None
        assert session_count.metric_value == 2.0

    @pytest.mark.asyncio
    async def test_compute_variant_metrics_empty_sessions(self) -> None:
        """compute_variant_metrics handles empty session list."""
        from collectors.rollup_job import RollupJob

        job = RollupJob()
        rollups = await job.compute_variant_metrics("variant-a", [])

        assert rollups == []

    @pytest.mark.asyncio
    async def test_compute_experiment_metrics_with_variants(self) -> None:
        """compute_experiment_metrics returns metrics for experiment."""
        from collectors.rollup_job import RollupJob

        job = RollupJob()
        variants = [
            {"variant_id": "variant-a", "metrics": {}},
            {"variant_id": "variant-b", "metrics": {}},
        ]

        rollups = await job.compute_experiment_metrics("exp-001", variants)

        assert isinstance(rollups, list)

        variant_count = next(
            (r for r in rollups if r.metric_name == "variant_count"),
            None,
        )
        assert variant_count is not None
        assert variant_count.metric_value == 2.0

    @pytest.mark.asyncio
    async def test_compute_experiment_metrics_empty_variants(self) -> None:
        """compute_experiment_metrics handles empty variant list."""
        from collectors.rollup_job import RollupJob

        job = RollupJob()
        rollups = await job.compute_experiment_metrics("exp-001", [])

        assert rollups == []


class TestPrometheusCollector:
    """Tests for the PrometheusCollector class."""

    @pytest.fixture
    def collector(self):
        """Create a PrometheusCollector instance for testing."""
        from collectors.prometheus_collector import PrometheusCollector

        return PrometheusCollector(
            base_url="http://localhost:9090",
            session_id=UUID("12345678-1234-1234-1234-123456789abc"),
        )

    def test_collector_initialization(self, collector) -> None:
        """PrometheusCollector initializes with correct attributes."""
        assert collector._base_url == "http://localhost:9090"
        assert str(collector._session_id) == "12345678-1234-1234-1234-123456789abc"

    def test_extract_values_from_matrix_success(self, collector) -> None:
        """_extract_values_from_matrix parses matrix result correctly."""
        result = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"__name__": "test"},
                        "values": [
                            [1625097600, "100.5"],
                            [1625097601, "200.5"],
                            [1625097602, "300.5"],
                        ],
                    }
                ],
            },
        }

        values = collector._extract_values_from_matrix(result)

        assert values == [100.5, 200.5, 300.5]

    def test_extract_values_from_matrix_empty_result(self, collector) -> None:
        """_extract_values_from_matrix handles empty results."""
        result = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [],
            },
        }

        values = collector._extract_values_from_matrix(result)

        assert values == []

    def test_extract_values_from_matrix_error_status(self, collector) -> None:
        """_extract_values_from_matrix handles error status."""
        result = {
            "status": "error",
            "error": "bad query",
        }

        values = collector._extract_values_from_matrix(result)

        assert values == []

    def test_extract_values_from_matrix_invalid_values(self, collector) -> None:
        """_extract_values_from_matrix skips invalid values."""
        result = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"__name__": "test"},
                        "values": [
                            [1625097600, "100.5"],
                            [1625097601, "not-a-number"],
                            [1625097602, "300.5"],
                        ],
                    }
                ],
            },
        }

        values = collector._extract_values_from_matrix(result)

        assert values == [100.5, 300.5]
