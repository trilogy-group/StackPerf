"""Direct tests for benchmark_core/services/common.py shared utilities."""

import warnings

import pytest

from benchmark_core.services.common import (
    render_env_dotenv,
    render_env_shell,
    validate_litellm_url,
    warn_revoke_failure,
)


class TestValidateLitellmUrl:
    def test_allows_https(self) -> None:
        assert validate_litellm_url("https://proxy.example.com") == "https://proxy.example.com"

    def test_allows_http_localhost(self) -> None:
        assert validate_litellm_url("http://localhost:4000") == "http://localhost:4000"

    def test_allows_http_127_0_0_1(self) -> None:
        assert validate_litellm_url("http://127.0.0.1:4000/") == "http://127.0.0.1:4000"

    def test_strips_trailing_slash(self) -> None:
        assert validate_litellm_url("https://proxy.example.com/") == "https://proxy.example.com"

    def test_rejects_http_in_production(self) -> None:
        with pytest.raises(ValueError, match="must use HTTPS"):
            validate_litellm_url("http://proxy.example.com")

    def test_allows_http_when_enforce_https_false(self) -> None:
        assert (
            validate_litellm_url("http://proxy.example.com", enforce_https=False)
            == "http://proxy.example.com"
        )


class TestRenderEnvShell:
    def test_basic(self) -> None:
        result = render_env_shell({"B": "2", "A": "1"})
        assert result == "export A='1'\nexport B='2'"

    def test_escapes_single_quotes(self) -> None:
        result = render_env_shell({"KEY": "it's fine"})
        assert result == "export KEY='it'\\''s fine'"

    def test_empty_dict(self) -> None:
        assert render_env_shell({}) == ""


class TestRenderEnvDotenv:
    def test_basic(self) -> None:
        result = render_env_dotenv({"B": "2", "A": "1"})
        assert result == "A=1\nB=2"

    def test_escapes_quotes_and_spaces(self) -> None:
        result = render_env_dotenv({"KEY": 'say "hello" now'})
        assert result == 'KEY="say \\"hello\\" now"'

    def test_empty_dict(self) -> None:
        assert render_env_dotenv({}) == ""


class TestWarnRevokeFailure:
    def test_emits_warning(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warn_revoke_failure("proxy_key", "key-123", RuntimeError("timeout"))
            assert len(w) == 1
            assert "key_id=key-123" in str(w[0].message)
            assert "timeout" in str(w[0].message)
            assert "Local metadata has been marked revoked" in str(w[0].message)

    def test_works_with_none_key_id(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warn_revoke_failure("credential", None, ValueError("bad request"))
            assert len(w) == 1
            assert "key_id=None" in str(w[0].message)
