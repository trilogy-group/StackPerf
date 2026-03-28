"""Unit tests for credential issuance service."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
import respx
from pydantic import SecretStr

from benchmark_core.models import ProxyCredential
from benchmark_core.services import CredentialService


class TestKeyAliasGeneration:
    """Test key aliasing convention for correlation."""

    @pytest.fixture
    def service(self) -> CredentialService:
        return CredentialService(master_key="test-master-key")

    def test_alias_format(self, service: CredentialService) -> None:
        """Key alias follows format: session-{session[:8]}-{exp[:8]}-{var[:8]}."""
        session_id = uuid4()
        experiment_id = "test-exp"
        variant_id = "test-var"

        alias = service._generate_key_alias(session_id, experiment_id, variant_id)

        assert alias.startswith("session-")
        # Should have at least: session prefix, session uuid fragment, exp fragment, var fragment
        parts = alias.split("-")
        assert len(parts) >= 4  # May be more if exp/var have hyphens
        assert parts[0] == "session"
        # Session UUID first 8 chars should be present
        assert str(session_id)[:8] in alias

    def test_alias_uniqueness(self, service: CredentialService) -> None:
        """Different sessions produce different aliases."""
        session1_id = uuid4()
        session2_id = uuid4()
        experiment_id = "test-experiment"
        variant_id = "test-variant"

        alias1 = service._generate_key_alias(session1_id, experiment_id, variant_id)
        alias2 = service._generate_key_alias(session2_id, experiment_id, variant_id)

        assert alias1 != alias2
        # Both should start with different session prefixes
        assert alias1[8:16] != alias2[8:16]

    def test_alias_short_ids(self, service: CredentialService) -> None:
        """Short experiment/variant IDs are handled gracefully."""
        session_id = uuid4()
        experiment_id = "ab"
        variant_id = "cd"

        alias = service._generate_key_alias(session_id, experiment_id, variant_id)

        assert "ab" in alias
        assert "cd" in alias


class TestMetadataTags:
    """Test metadata tag generation for correlation."""

    @pytest.fixture
    def service(self) -> CredentialService:
        return CredentialService(master_key="test-master-key")

    def test_metadata_includes_session_dimensions(self, service: CredentialService) -> None:
        """Metadata tags include all session correlation dimensions."""
        session_id = uuid4()
        experiment_id = "exp-123"
        variant_id = "var-456"
        harness_profile = "claude-code"

        metadata = service._build_metadata_tags(
            session_id, experiment_id, variant_id, harness_profile
        )

        assert metadata["benchmark_session_id"] == str(session_id)
        assert metadata["benchmark_experiment_id"] == experiment_id
        assert metadata["benchmark_variant_id"] == variant_id
        assert metadata["benchmark_harness_profile"] == harness_profile
        assert metadata["benchmark_source"] == "opensymphony"

    def test_metadata_joinable_to_session(self, service: CredentialService) -> None:
        """Metadata can be joined back to session via session_id."""
        session_id = uuid4()

        metadata = service._build_metadata_tags(session_id, "exp", "var", "harness")

        # Can reconstruct the session UUID from metadata
        reconstructed = UUID(metadata["benchmark_session_id"])
        assert reconstructed == session_id


class TestCredentialIssuance:
    """Test full credential issuance flow."""

    @pytest.fixture
    def service(self) -> CredentialService:
        return CredentialService(
            litellm_base_url="http://localhost:4000",
            master_key="test-master-key",
        )

    @pytest.mark.asyncio
    @respx.mock
    async def test_credential_has_all_fields(self, service: CredentialService) -> None:
        """Issued credential contains all required metadata."""
        session_id = uuid4()
        experiment_id = "test-experiment"
        variant_id = "test-variant"
        harness_profile = "claude-code"

        # Mock LiteLLM API response
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "key": "sk-litellm-test-key-12345",
                    "key_id": "litellm-key-id-123",
                },
            )
        )

        credential = await service.issue_credential(
            session_id=session_id,
            experiment_id=experiment_id,
            variant_id=variant_id,
            harness_profile=harness_profile,
        )

        assert isinstance(credential.credential_id, UUID)
        assert credential.session_id == session_id
        assert credential.experiment_id == experiment_id
        assert credential.variant_id == variant_id
        assert credential.harness_profile == harness_profile
        assert credential.key_alias.startswith("session-")
        assert credential.is_active is True
        assert credential.expires_at is not None
        assert credential.litellm_key_id == "litellm-key-id-123"

    @pytest.mark.asyncio
    @respx.mock
    async def test_credential_has_secret(self, service: CredentialService) -> None:
        """Issued credential contains a secret API key."""
        # Mock LiteLLM API response
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "key": "sk-litellm-test-key-from-api",
                    "key_id": "key-123",
                },
            )
        )

        credential = await service.issue_credential(
            session_id=uuid4(),
            experiment_id="exp",
            variant_id="var",
            harness_profile="harness",
        )

        assert isinstance(credential.api_key, SecretStr)
        key_value = credential.api_key.get_secret_value()
        assert key_value == "sk-litellm-test-key-from-api"

    @pytest.mark.asyncio
    @respx.mock
    async def test_credential_expiration(self, service: CredentialService) -> None:
        """Credential has configurable TTL."""
        now = datetime.now(UTC)

        # Mock LiteLLM API response
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "key": "sk-test-key",
                    "key_id": "key-123",
                },
            )
        )

        credential = await service.issue_credential(
            session_id=uuid4(),
            experiment_id="exp",
            variant_id="var",
            harness_profile="harness",
            ttl_hours=48,
        )

        assert credential.expires_at is not None
        # Should expire roughly 48 hours from now
        time_diff = credential.expires_at - now  # type: ignore[operator]
        assert timedelta(hours=47) < time_diff < timedelta(hours=49)

    @pytest.mark.asyncio
    async def test_credential_requires_master_key(self) -> None:
        """Credential issuance requires master_key."""
        service = CredentialService(master_key=None)

        with pytest.raises(RuntimeError, match="master_key not configured"):
            await service.issue_credential(
                session_id=uuid4(),
                experiment_id="exp",
                variant_id="var",
                harness_profile="harness",
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_credential_handles_api_error(self, service: CredentialService) -> None:
        """Credential issuance handles LiteLLM API errors."""
        # Mock LiteLLM API error response
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        with pytest.raises(RuntimeError, match="LiteLLM API error"):
            await service.issue_credential(
                session_id=uuid4(),
                experiment_id="exp",
                variant_id="var",
                harness_profile="harness",
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_credential_handles_missing_key(self, service: CredentialService) -> None:
        """Credential issuance handles missing key in response."""
        # Mock LiteLLM API response without key
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(200, json={"key_id": "123"})
        )

        with pytest.raises(RuntimeError, match="missing 'key' field"):
            await service.issue_credential(
                session_id=uuid4(),
                experiment_id="exp",
                variant_id="var",
                harness_profile="harness",
            )


class TestCredentialRevocation:
    """Test credential revocation."""

    @pytest.fixture
    def service(self) -> CredentialService:
        return CredentialService(
            litellm_base_url="http://localhost:4000",
            master_key="test-master-key",
        )

    @pytest.fixture
    async def active_credential(self, service: CredentialService) -> ProxyCredential:
        # Mock LiteLLM API response
        with respx.mock:
            respx.post("http://localhost:4000/key/generate").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "key": "sk-test-key",
                        "key_id": "litellm-key-id-123",
                    },
                )
            )
            return await service.issue_credential(
                session_id=uuid4(),
                experiment_id="exp",
                variant_id="var",
                harness_profile="harness",
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_revoke_marks_inactive(
        self, service: CredentialService, active_credential: ProxyCredential
    ) -> None:
        """Revocation marks credential as inactive."""
        # Mock LiteLLM delete API
        respx.post("http://localhost:4000/key/delete").mock(
            return_value=httpx.Response(200, json={"deleted_keys": ["litellm-key-id-123"]})
        )

        revoked = await service.revoke_credential(active_credential)

        assert revoked.is_active is False
        assert revoked.revoked_at is not None

    @pytest.mark.asyncio
    async def test_revoke_clears_secret(
        self, service: CredentialService, active_credential: ProxyCredential
    ) -> None:
        """Revocation clears the secret from memory."""
        revoked = await service.revoke_credential(active_credential)

        assert revoked.api_key.get_secret_value() == "REDACTED"


class TestEnvRendering:
    """Test environment variable rendering."""

    @pytest.fixture
    def service(self) -> CredentialService:
        return CredentialService(master_key="test-master-key")

    @pytest.fixture
    async def credential(self, service: CredentialService) -> ProxyCredential:
        with respx.mock:
            respx.post("http://localhost:4000/key/generate").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "key": "sk-test-key-for-env",
                        "key_id": "key-123",
                    },
                )
            )
            return await service.issue_credential(
                session_id=uuid4(),
                experiment_id="exp",
                variant_id="var",
                harness_profile="harness",
            )

    @pytest.mark.asyncio
    @respx.mock
    async def test_render_env_dict(
        self, service: CredentialService, credential: ProxyCredential
    ) -> None:
        """Environment snippet includes required variables."""
        env = service.render_env_snippet(
            credential=credential,
            proxy_base_url="http://localhost:4000",
            model="gpt-4o",
        )

        assert env["OPENAI_API_BASE"] == "http://localhost:4000"
        assert env["OPENAI_API_KEY"] == credential.api_key.get_secret_value()
        assert env["OPENAI_MODEL"] == "gpt-4o"
        assert env["LITELLM_SESSION_ALIAS"] == credential.key_alias

    def test_render_shell_format(self, service: CredentialService) -> None:
        """Shell format produces valid export commands."""
        env = {
            "KEY1": "value1",
            "KEY2": "value with spaces",
        }

        shell = service.render_env_shell(env)

        assert "export KEY1='value1'" in shell
        assert "export KEY2='value with spaces'" in shell

    def test_render_shell_escapes_quotes(self, service: CredentialService) -> None:
        """Shell format properly escapes single quotes."""
        env = {"KEY": "value'with'quotes"}

        shell = service.render_env_shell(env)

        # Should escape single quotes for shell safety
        assert "'\\''" in shell

    def test_render_dotenv_format(self, service: CredentialService) -> None:
        """Dotenv format produces valid .env content."""
        env = {
            "KEY1": "value1",
            "KEY2": "value with spaces",
        }

        dotenv = service.render_env_dotenv(env)

        assert "KEY1=value1" in dotenv
        assert 'KEY2="value with spaces"' in dotenv

    def test_render_dotenv_escapes_special(self, service: CredentialService) -> None:
        """Dotenv format escapes special characters."""
        env = {"KEY": 'value"with"quotes'}

        dotenv = service.render_env_dotenv(env)

        assert '\\"' in dotenv


class TestCredentialCorrelation:
    """Test that credentials can be correlated back to sessions."""

    @pytest.fixture
    def service(self) -> CredentialService:
        return CredentialService(master_key="test-master-key")

    @pytest.mark.asyncio
    async def test_alias_contains_session_reference(self, service: CredentialService) -> None:
        """Key alias contains truncated session ID for correlation."""
        session_id = uuid4()

        alias = service._generate_key_alias(session_id, "exp", "var")

        # First 8 chars of session UUID should be in alias
        session_prefix = str(session_id)[:8]
        assert session_prefix in alias

    @pytest.mark.asyncio
    async def test_metadata_enables_join(self, service: CredentialService) -> None:
        """Metadata tags enable joining back to session."""
        session_id = uuid4()
        experiment_id = "my-experiment"
        variant_id = "my-variant"

        metadata = service._build_metadata_tags(session_id, experiment_id, variant_id, "harness")

        # Each dimension is present and can be used for joining
        assert metadata["benchmark_session_id"] == str(session_id)
        assert metadata["benchmark_experiment_id"] == experiment_id
        assert metadata["benchmark_variant_id"] == variant_id

    @pytest.mark.asyncio
    @respx.mock
    async def test_full_correlation_chain(self, service: CredentialService) -> None:
        """Complete chain from credential back to session works."""
        session_id = uuid4()
        experiment_id = "test-exp"
        variant_id = "test-var"
        harness_profile = "test-harness"

        # Mock LiteLLM API response
        respx.post("http://localhost:4000/key/generate").mock(
            return_value=httpx.Response(
                200,
                json={
                    "key": "sk-test-key-correlation",
                    "key_id": "key-correlation-123",
                },
            )
        )

        # Issue credential
        credential = await service.issue_credential(
            session_id=session_id,
            experiment_id=experiment_id,
            variant_id=variant_id,
            harness_profile=harness_profile,
        )

        # From credential, we can get:
        # 1. Session ID directly
        assert credential.session_id == session_id

        # 2. Key alias that includes session reference
        assert str(session_id)[:8] in credential.key_alias

        # 3. Metadata tags for all dimensions
        # (would be sent to LiteLLM with the key)
        metadata = service._build_metadata_tags(
            session_id, experiment_id, variant_id, harness_profile
        )
        assert metadata["benchmark_session_id"] == str(session_id)


class TestHTTPSValidation:
    """Test HTTPS validation for LiteLLM URL."""

    def test_accepts_localhost(self) -> None:
        """Accepts localhost URLs."""
        service = CredentialService(
            litellm_base_url="http://localhost:4000",
            master_key="test-key",
        )
        assert service.litellm_base_url == "http://localhost:4000"

    def test_accepts_127_0_0_1(self) -> None:
        """Accepts 127.0.0.1 URLs."""
        service = CredentialService(
            litellm_base_url="http://127.0.0.1:4000",
            master_key="test-key",
        )
        assert service.litellm_base_url == "http://127.0.0.1:4000"

    def test_accepts_https(self) -> None:
        """Accepts HTTPS URLs."""
        service = CredentialService(
            litellm_base_url="https://litellm.example.com",
            master_key="test-key",
        )
        assert service.litellm_base_url == "https://litellm.example.com"

    def test_rejects_http_in_production(self) -> None:
        """Rejects HTTP in production environments."""
        with pytest.raises(ValueError, match="must use HTTPS"):
            CredentialService(
                litellm_base_url="http://litellm.example.com",
                master_key="test-key",
            )

    def test_can_disable_https_check(self) -> None:
        """Can disable HTTPS check for testing."""
        service = CredentialService(
            litellm_base_url="http://litellm.example.com",
            master_key="test-key",
            enforce_https=False,
        )
        assert service.litellm_base_url == "http://litellm.example.com"
