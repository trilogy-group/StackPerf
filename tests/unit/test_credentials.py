"""Unit tests for credential metadata builder.

Tests the credential issuance and correlation metadata.
"""

import pytest
from datetime import datetime, timedelta

from benchmark_core.config import Settings
from benchmark_core.models import ProxyCredential
from benchmark_core.services import CredentialIssuer, build_credential_metadata


class TestCredentialIssuer:
    """Test credential generation."""

    def test_generate_session_credential(self):
        """Every session gets a unique credential."""
        issuer = CredentialIssuer()

        cred = issuer.generate_session_credential(
            session_id="test-session-123",
        )

        assert cred is not None
        assert cred.key_alias.startswith("bench-session-")
        assert cred.virtual_key_id is not None
        assert cred.expires_at is not None

    def test_credential_with_metadata(self):
        """Key metadata can be joined back to session."""
        issuer = CredentialIssuer()

        cred = issuer.generate_session_credential(
            session_id="session-abc",
            experiment_id="exp-123",
            variant_id="var-456",
            task_card_id="task-789",
            harness_profile_id="harness-c34",
        )

        assert cred.metadata["session_id"] == "session-abc"
        assert cred.metadata["experiment_id"] == "exp-123"
        assert cred.metadata["variant_id"] == "var-456"

    def test_credential_ttl(self):
        """Credentials have configurable TTL."""
        issuer = CredentialIssuer(Settings(session_credential_ttl_hours=48))

        cred = issuer.generate_session_credential(
            session_id="session-test",
        )

        expected_expiry = datetime.utcnow() + timedelta(hours=48)
        # Allow 1 minute tolerance for test execution time
        assert cred.expires_at is not None
        delta = abs((cred.expires_at - expected_expiry).total_seconds())
        assert delta < 60

    def test_different_sessions_different_credentials(self):
        """Each session gets a unique credential."""
        issuer = CredentialIssuer()

        cred1 = issuer.generate_session_credential(session_id="session-1")
        cred2 = issuer.generate_session_credential(session_id="session-2")

        assert cred1.key_alias != cred2.key_alias
        assert cred1.virtual_key_id != cred2.virtual_key_id

    def test_generate_api_key_value(self):
        """API key value can be generated once at creation."""
        issuer = CredentialIssuer()

        cred = issuer.generate_session_credential(session_id="test")
        key_value = issuer.generate_api_key_value(cred)

        assert key_value is not None
        assert len(key_value) > 32  # Secure random key

    def test_raw_key_not_stored_in_credential(self):
        """Raw key is not persisted in plaintext beyond storage boundary."""
        issuer = CredentialIssuer()

        cred = issuer.generate_session_credential(session_id="test")

        # The Pydantic model should not include _raw_key in serialization
        cred_dict = cred.model_dump()
        assert "_raw_key" not in cred_dict
        # The raw key is only accessible via generate_api_key_value


class TestBuildCredentialMetadata:
    """Test credential metadata builder."""

    def test_basic_metadata(self):
        """Basic metadata includes session ID and system identifier."""
        metadata = build_credential_metadata(
            session_id="session-123",
        )

        assert metadata["session_id"] == "session-123"
        assert metadata["benchmark_system"] == "stackperf"
        assert "created_at" in metadata

    def test_full_correlation_metadata(self):
        """Full metadata includes all correlation keys."""
        metadata = build_credential_metadata(
            session_id="session-123",
            experiment_id="exp-abc",
            variant_id="var-def",
            task_card_id="task-ghi",
            harness_profile_id="harness-jkl",
        )

        assert metadata["session_id"] == "session-123"
        assert metadata["experiment_id"] == "exp-abc"
        assert metadata["variant_id"] == "var-def"
        assert metadata["task_card_id"] == "task-ghi"
        assert metadata["harness_profile_id"] == "harness-jkl"

    def test_extra_metadata(self):
        """Extra metadata fields can be added."""
        metadata = build_credential_metadata(
            session_id="session-123",
            custom_field="custom-value",
            another_field="another-value",
        )

        assert metadata["custom_field"] == "custom-value"
        assert metadata["another_field"] == "another-value"

    def test_no_secrets_in_metadata(self):
        """Metadata should not contain secrets."""
        metadata = build_credential_metadata(
            session_id="session-123",
        )

        # Check that no secret-like fields are present
        for key in metadata:
            assert "secret" not in key.lower()
            assert "key" not in key.lower() or key == "session_id"
            assert "password" not in key.lower()
            assert "token" not in key.lower()
