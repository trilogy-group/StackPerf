"""Unit tests for domain models and constraints."""
import pytest
from datetime import datetime
from uuid import UUID

from benchmark_core.models import (
    Provider,
    HarnessProfile,
    Variant,
    Experiment,
    TaskCard,
    Session,
    Request,
    MetricRollup,
    Artifact,
    SessionStatus,
    RequestStatus,
    RollupScopeType,
)


class TestSessionStatus:
    """Tests for SessionStatus enum."""

    def test_all_statuses_defined(self):
        """All expected statuses should exist."""
        assert SessionStatus.PENDING == "pending"
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.COMPLETED == "completed"
        assert SessionStatus.ABORTED == "aborted"
        assert SessionStatus.INVALID == "invalid"

    def test_status_is_string_enum(self):
        """Status should be string-convertible."""
        assert SessionStatus.PENDING.value == "pending"
        assert SessionStatus.COMPLETED == "completed"


class TestRequestStatus:
    """Tests for RequestStatus enum."""

    def test_all_statuses_defined(self):
        """All expected statuses should exist."""
        assert RequestStatus.SUCCESS == "success"
        assert RequestStatus.ERROR == "error"
        assert RequestStatus.TIMEOUT == "timeout"
        assert RequestStatus.CANCELLED == "cancelled"


class TestRollupScopeType:
    """Tests for RollupScopeType enum."""

    def test_all_scopes_defined(self):
        """All expected scopes should exist."""
        assert RollupScopeType.REQUEST == "request"
        assert RollupScopeType.SESSION == "session"
        assert RollupScopeType.VARIANT == "variant"
        assert RollupScopeType.EXPERIMENT == "experiment"


class TestProvider:
    """Tests for Provider model."""

    def test_create_provider(self):
        """Should create provider with defaults."""
        provider = Provider(
            name="test-provider",
            route_name="test-route",
            protocol_surface="anthropic_messages",
        )
        assert provider.name == "test-provider"
        assert provider.provider_id is not None
        assert isinstance(provider.provider_id, UUID)
        assert provider.created_at is not None

    def test_provider_with_upstream_url(self):
        """Should accept optional upstream URL."""
        provider = Provider(
            name="test-provider",
            route_name="test-route",
            protocol_surface="openai_responses",
            upstream_base_url="https://api.example.com",
        )
        assert provider.upstream_base_url == "https://api.example.com"


class TestSession:
    """Tests for Session model."""

    def test_create_session_defaults(self):
        """Should create session with default status."""
        from uuid import uuid4
        
        session = Session(
            experiment_id=uuid4(),
            variant_id=uuid4(),
            task_card_id=uuid4(),
            harness_profile_id=uuid4(),
        )
        assert session.status == SessionStatus.PENDING
        assert session.session_id is not None
        assert session.started_at is not None
        assert session.ended_at is None

    def test_session_with_git_metadata(self):
        """Should capture git context."""
        from uuid import uuid4
        
        session = Session(
            experiment_id=uuid4(),
            variant_id=uuid4(),
            task_card_id=uuid4(),
            harness_profile_id=uuid4(),
            git_branch="main",
            git_commit_sha="abc123",
            git_dirty=True,
        )
        assert session.git_branch == "main"
        assert session.git_commit_sha == "abc123"
        assert session.git_dirty is True


class TestRequest:
    """Tests for Request model."""

    def test_create_request_defaults(self):
        """Should create request with default status."""
        request = Request()
        assert request.status == RequestStatus.SUCCESS
        assert request.request_id is not None

    def test_request_with_timing(self):
        """Should capture timing metrics."""
        request = Request(
            latency_ms=1234.5,
            ttft_ms=100.0,
            proxy_overhead_ms=5.0,
            provider_latency_ms=1229.5,
        )
        assert request.latency_ms == 1234.5
        assert request.ttft_ms == 100.0


class TestMetricRollup:
    """Tests for MetricRollup model."""

    def test_create_rollup(self):
        """Should create rollup with required fields."""
        from uuid import uuid4
        
        rollup = MetricRollup(
            scope_type=RollupScopeType.SESSION,
            scope_id=uuid4(),
            metric_name="median_latency_ms",
            metric_value=123.45,
        )
        assert rollup.scope_type == RollupScopeType.SESSION
        assert rollup.metric_name == "median_latency_ms"
        assert rollup.metric_value == 123.45
