"""Unit tests for sessionless proxy key service."""

from uuid import uuid4

import httpx
import pytest
import respx
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from benchmark_core.db.models import Base
from benchmark_core.models import ProxyKey, ProxyKeyStatus
from benchmark_core.repositories.proxy_key_repository import SQLProxyKeyRepository
from benchmark_core.services.proxy_key_service import (
    LiteLLMAPIError,
    ProxyKeyService,
    ProxyKeyServiceError,
)


@pytest.fixture
def test_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    """Create a database session for testing."""
    session_local = sessionmaker(bind=test_engine)
    session = session_local()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def repository(db_session):
    """Create a SQLProxyKeyRepository."""
    return SQLProxyKeyRepository(db_session)


@pytest.fixture
def service(repository):
    """Create a ProxyKeyService with test config."""
    return ProxyKeyService(
        repository=repository,
        litellm_base_url="http://localhost:4000",
        master_key="test-master-key",
        enforce_https=False,
    )


class TestProxyKeyCreation:
    """Test proxy key creation via LiteLLM API."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_key_success(self, service):
        """Successful key creation returns metadata and secret."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "key": "sk-litellm-test-key-12345",
                    "key_id": "litellm-key-id-123",
                },
            )
        )

        proxy_key, secret = await service.create_key(
            key_alias="test-alias",
            owner="alice",
            team="platform",
            customer="internal",
            allowed_models=["gpt-4o"],
            ttl_hours=24,
        )

        assert isinstance(proxy_key, ProxyKey)
        assert proxy_key.key_alias == "test-alias"
        assert proxy_key.owner == "alice"
        assert proxy_key.team == "platform"
        assert proxy_key.customer == "internal"
        assert proxy_key.allowed_models == ["gpt-4o"]
        assert proxy_key.status == ProxyKeyStatus.ACTIVE
        assert proxy_key.litellm_key_id == "litellm-key-id-123"
        assert isinstance(secret, SecretStr)
        assert secret.get_secret_value() == "sk-litellm-test-key-12345"

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_key_auto_alias(self, service):
        """Auto-generates alias when not provided."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={"key": "sk-auto-key", "key_id": "auto-id"},
            )
        )

        proxy_key, secret = await service.create_key()

        assert proxy_key.key_alias.startswith("usage-")
        assert len(proxy_key.key_alias) > 8

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_key_persists_metadata(self, service, repository, db_session):
        """Key metadata is persisted to the database (no secret)."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={"key": "sk-secret-123", "key_id": "kid-123"},
            )
        )

        proxy_key, secret = await service.create_key(
            key_alias="persist-test",
            owner="bob",
            team="dev",
        )

        # Force commit for in-memory SQLite
        db_session.commit()

        # Verify in database - no secret stored
        orm = await repository.get_by_alias("persist-test")
        assert orm is not None
        assert orm.key_alias == "persist-test"
        assert orm.owner == "bob"
        assert orm.team == "dev"
        # Secret must NOT be in the ORM
        assert not hasattr(orm, "api_key")

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_key_with_usage_policy(self, service):
        """Usage policy defaults are applied."""
        from benchmark_core.config import UsagePolicyProfile

        policy = UsagePolicyProfile(
            name="team-policy",
            owner="default-owner",
            team="default-team",
            customer="default-customer",
            allowed_models=["kimi-k2-5"],
            budget_duration="30d",
            budget_amount=500.0,
            ttl_seconds=7200,
        )

        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={"key": "sk-policy-key", "key_id": "policy-id"},
            )
        )

        proxy_key, secret = await service.create_key(
            usage_policy=policy,
            owner="override-owner",
        )

        assert proxy_key.owner == "override-owner"  # explicit override
        assert proxy_key.team == "default-team"  # from policy
        assert proxy_key.customer == "default-customer"
        assert proxy_key.allowed_models == ["kimi-k2-5"]
        assert proxy_key.budget_duration == "30d"
        assert proxy_key.budget_amount == 500.0
        # ttl_seconds=7200 rounds up to 2 hours (effective TTL applied)
        assert proxy_key.expires_at is not None
        assert proxy_key.created_at is not None
        delta = proxy_key.expires_at - proxy_key.created_at
        assert abs(delta.total_seconds() - 7200) < 1  # allow <1s timing jitter

    @pytest.mark.asyncio
    async def test_create_key_requires_master_key(self, repository):
        """Key creation fails without master_key."""
        svc = ProxyKeyService(
            repository=repository,
            litellm_base_url="http://localhost:4000",
            master_key=None,
            enforce_https=False,
        )

        with pytest.raises(ProxyKeyServiceError, match="master_key not configured"):
            await svc.create_key()

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_key_handles_api_error(self, service):
        """LiteLLM API errors are surfaced."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with pytest.raises(LiteLLMAPIError, match="LiteLLM API error"):
            await service.create_key()

    @pytest.mark.asyncio
    @respx.mock
    async def test_create_key_handles_missing_key_field(self, service):
        """Missing 'key' in LiteLLM response raises error."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(200, json={"key_id": "no-key"})
        )

        with pytest.raises(LiteLLMAPIError, match="missing 'key' field"):
            await service.create_key()


class TestProxyKeyListing:
    """Test proxy key listing operations."""

    @pytest.mark.asyncio
    async def test_list_keys_empty(self, service):
        """Empty repository returns empty list."""
        keys = await service.list_keys()
        assert keys == []

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_keys_filter_by_owner(self, service, db_session):
        """Filtering by owner returns matching keys."""
        respx.post("http://localhost:4000/key/generate").mock(
            side_effect=[
                httpx.Response(200, json={"key": "sk-1", "key_id": "id-1"}),
                httpx.Response(200, json={"key": "sk-2", "key_id": "id-2"}),
            ]
        )

        await service.create_key(key_alias="k1", owner="alice")
        await service.create_key(key_alias="k2", owner="bob")
        db_session.commit()

        alice_keys = await service.list_keys(owner="alice")
        assert len(alice_keys) == 1
        assert alice_keys[0].key_alias == "k1"
        assert alice_keys[0].owner == "alice"

    @pytest.mark.asyncio
    @respx.mock
    async def test_list_keys_filter_by_status(self, service, db_session):
        """Filtering by status returns matching keys."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(200, json={"key": "sk-1", "key_id": "id-1"})
        )

        proxy_key, _ = await service.create_key(key_alias="status-test")
        db_session.commit()

        active_keys = await service.list_keys(status=ProxyKeyStatus.ACTIVE)
        assert len(active_keys) == 1
        assert active_keys[0].status == ProxyKeyStatus.ACTIVE


class TestProxyKeyRevocation:
    """Test proxy key revocation."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_revoke_key_marks_inactive(self, service, db_session):
        """Revocation marks key as revoked locally."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(200, json={"key": "sk-1", "key_id": "id-1"})
        )
        respx.post("http://localhost:4000/key/delete").mock(
            return_value=httpx.Response(200, json={"deleted_keys": ["id-1"]})
        )

        proxy_key, _ = await service.create_key(key_alias="revoke-test")
        db_session.commit()

        revoked = await service.revoke_key(proxy_key.proxy_key_id)
        assert revoked is not None
        assert revoked.status == ProxyKeyStatus.REVOKED
        assert revoked.revoked_at is not None

    @pytest.mark.asyncio
    @respx.mock
    async def test_revoke_key_not_found(self, service):
        """Revoking non-existent key returns None."""
        result = await service.revoke_key(uuid4())
        assert result is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_revoke_key_silences_litellm_error(self, service, db_session):
        """LiteLLM delete errors are silently ignored."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(200, json={"key": "sk-1", "key_id": "id-1"})
        )
        respx.post("http://localhost:4000/key/delete").mock(
            return_value=httpx.Response(404, text="Not Found")
        )

        proxy_key, _ = await service.create_key(key_alias="silent-revoke")
        db_session.commit()

        # Should not raise despite 404 from LiteLLM
        revoked = await service.revoke_key(proxy_key.proxy_key_id)
        assert revoked is not None
        assert revoked.status == ProxyKeyStatus.REVOKED

    @pytest.mark.asyncio
    @respx.mock
    async def test_revoke_already_revoked(self, service, db_session):
        """Revoking an already revoked key is a no-op."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(200, json={"key": "sk-1", "key_id": "id-1"})
        )
        respx.post("http://localhost:4000/key/delete").mock(
            return_value=httpx.Response(200, json={"deleted_keys": ["id-1"]})
        )

        proxy_key, _ = await service.create_key(key_alias="double-revoke")
        db_session.commit()

        revoked = await service.revoke_key(proxy_key.proxy_key_id)
        db_session.commit()
        assert revoked is not None
        assert revoked.status == ProxyKeyStatus.REVOKED

        second = await service.revoke_key(proxy_key.proxy_key_id)
        assert second is not None
        assert second.status == ProxyKeyStatus.REVOKED


class TestProxyKeyInfo:
    """Test proxy key info retrieval."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_key_info(self, service, db_session):
        """Retrieve key info by ID."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(200, json={"key": "sk-1", "key_id": "id-1"})
        )

        proxy_key, _ = await service.create_key(key_alias="info-test", owner="alice")
        db_session.commit()

        found = await service.get_key_info(proxy_key.proxy_key_id)
        assert found is not None
        assert found.key_alias == "info-test"
        assert found.owner == "alice"

    @pytest.mark.asyncio
    async def test_get_key_info_not_found(self, service):
        """Missing key returns None."""
        found = await service.get_key_info(uuid4())
        assert found is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_get_key_by_alias(self, service, db_session):
        """Retrieve key by alias."""
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(200, json={"key": "sk-1", "key_id": "id-1"})
        )

        proxy_key, _ = await service.create_key(key_alias="alias-lookup")
        db_session.commit()

        found = await service.get_key_by_alias("alias-lookup")
        assert found is not None
        assert found.proxy_key_id == proxy_key.proxy_key_id


class TestEnvRendering:
    """Test environment snippet rendering."""

    def test_render_env_snippet_basic(self, service):
        """Basic OpenAI-compatible env vars."""
        secret = SecretStr("sk-test-key")
        env = service.render_env_snippet(secret, proxy_base_url="http://proxy:4000")

        assert env["OPENAI_API_BASE"] == "http://proxy:4000"
        assert env["OPENAI_API_KEY"] == "sk-test-key"

    def test_render_env_snippet_with_model(self, service):
        """Includes model when provided."""
        secret = SecretStr("sk-test-key")
        env = service.render_env_snippet(secret, proxy_base_url="http://proxy:4000", model="gpt-4o")

        assert env["OPENAI_MODEL"] == "gpt-4o"

    def test_render_env_shell(self, service):
        """Shell format produces export commands."""
        env = {"KEY1": "value1", "KEY2": "value with spaces"}
        shell = service.render_env_shell(env)

        assert "export KEY1='value1'" in shell
        assert "export KEY2='value with spaces'" in shell

    def test_render_env_dotenv(self, service):
        """Dotenv format produces .env content."""
        env = {"KEY1": "value1", "KEY2": "value with spaces"}
        dotenv = service.render_env_dotenv(env)

        assert "KEY1=value1" in dotenv
        assert 'KEY2="value with spaces"' in dotenv


class TestHTTPSValidation:
    """Test HTTPS validation."""

    def test_accepts_localhost(self, repository):
        """Accepts localhost URLs."""
        svc = ProxyKeyService(
            repository=repository,
            litellm_base_url="http://localhost:4000",
            master_key="test",
            enforce_https=False,
        )
        assert svc.litellm_base_url == "http://localhost:4000"

    def test_rejects_http_in_production(self, repository):
        """Rejects HTTP in production."""
        with pytest.raises(ValueError, match="must use HTTPS"):
            ProxyKeyService(
                repository=repository,
                litellm_base_url="http://example.com",
                master_key="test",
                enforce_https=True,
            )

    def test_accepts_https(self, repository):
        """Accepts HTTPS URLs."""
        svc = ProxyKeyService(
            repository=repository,
            litellm_base_url="https://litellm.example.com",
            master_key="test",
            enforce_https=True,
        )
        assert svc.litellm_base_url == "https://litellm.example.com"
