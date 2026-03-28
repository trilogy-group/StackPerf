#!/usr/bin/env python3
"""Demo script showing security features in action.

This demonstrates:
1. Secret redaction working on real patterns
2. Default-off content capture
3. Retention policy calculations
"""

from benchmark_core.security import (
    ContentCaptureConfig,
    RedactionFilter,
    RetentionPolicy,
    RetentionSettings,
    get_redaction_filter,
    redact_for_logging,
    should_capture_content,
)
from datetime import UTC, datetime, timedelta


def demo_redaction() -> None:
    """Demonstrate secret redaction in action."""
    print("\n" + "=" * 60)
    print("SECRET REDACTION DEMO")
    print("=" * 60)

    filter = get_redaction_filter()

    # Test API key redaction
    api_key_data = {
        "api_key": "sk-test12345678901234567890abcdef",
        "model": "gpt-4",
        "provider": "openai",
    }
    print("\n--- API Key Redaction ---")
    print(f"Original:  {api_key_data}")
    print(f"Redacted:  {filter.redact_dict(api_key_data)}")

    # Test database URL redaction
    db_url_data = {
        "connection_string": "postgresql://admin:secretpass123@db.example.com:5432/production",
        "pool_size": 10,
    }
    print("\n--- Database URL Redaction ---")
    print(f"Original:  {db_url_data}")
    print(f"Redacted:  {filter.redact_dict(db_url_data)}")

    # Test bearer token redaction
    token_data = {
        "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ",
    }
    print("\n--- Bearer Token Redaction ---")
    print(f"Original:  {token_data}")
    print(f"Redacted:  {filter.redact_dict(token_data)}")

    # Test environment variable redaction
    env_data = {
        "OPENAI_API_KEY": "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz",
        "DATABASE_PASSWORD": "super_secret_password_123!",
        "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
    }
    print("\n--- Environment Variable Redaction ---")
    print(f"Original:  {env_data}")
    print(f"Redacted:  {filter.redact_dict(env_data)}")

    # Test nested data structures
    nested_data = {
        "session": {
            "id": "session-123",
            "credentials": {
                "api_key": "sk-ant-api03-1234567890abcdefghijklmnopqrstuvwxyz",
                "token": "Bearer token_12345678901234567890abcdef",
            },
        },
        "requests": [
            {"model": "gpt-4", "key": "sk-test12345678901234567890xyz"},
            {"model": "claude-3", "key": "sk-ant-test1234567890abcdefghijklm"},
        ],
    }
    print("\n--- Nested Structure Redaction ---")
    print(f"Original:  {nested_data}")
    print(f"Redacted:  {filter.redact_dict(nested_data)}")

    # Test convenience function
    print("\n--- Convenience Function (redact_for_logging) ---")
    test_data = {"secret": "sk-test12345678901234567890secret"}
    print(f"Original:  {test_data}")
    print(f"Redacted:  {redact_for_logging(test_data)}")


def demo_content_capture() -> None:
    """Demonstrate default-off content capture."""
    print("\n" + "=" * 60)
    print("CONTENT CAPTURE CONFIGURATION DEMO")
    print("=" * 60)

    # Default config - content capture is OFF
    default_config = ContentCaptureConfig()
    print("\n--- Default Configuration (Content Capture OFF) ---")
    print(f"enabled: {default_config.enabled}")
    print(f"capture_prompts: {default_config.capture_prompts}")
    print(f"capture_responses: {default_config.capture_responses}")
    print(f"should_capture_prompt(): {default_config.should_capture_prompt()}")
    print(f"should_capture_response(): {default_config.should_capture_response()}")

    # Check using helper function
    print("\n--- Using Helper Function ---")
    print(f"should_capture_content('prompt'): {should_capture_content('prompt')}")
    print(f"should_capture_content('response'): {should_capture_content('response')}")

    # Explicit opt-in configuration
    opt_in_config = ContentCaptureConfig(
        enabled=True,
        capture_prompts=True,
        capture_responses=True,
    )
    print("\n--- Opt-In Configuration (Explicitly Enabled) ---")
    print(f"enabled: {opt_in_config.enabled}")
    print(f"capture_prompts: {opt_in_config.capture_prompts}")
    print(f"capture_responses: {opt_in_config.capture_responses}")
    print(f"should_capture_prompt(): {opt_in_config.should_capture_prompt()}")
    print(f"should_capture_response(): {opt_in_config.should_capture_response()}")


def demo_retention() -> None:
    """Demonstrate retention policy calculations."""
    print("\n" + "=" * 60)
    print("RETENTION POLICY DEMO")
    print("=" * 60)

    # Default retention settings
    settings = RetentionSettings()
    print("\n--- Default Retention Settings ---")
    print(f"raw_ingestion: {settings.raw_ingestion.retention_days} days")
    print(f"normalized_requests: {settings.normalized_requests.retention_days} days")
    print(f"sessions: {settings.sessions.retention_days} days")
    print(f"session_credentials: {settings.session_credentials.retention_days} days")
    print(f"artifacts: {settings.artifacts.retention_days} days (archive: {settings.artifacts.archive_before_delete})")
    print(f"metric_rollups: {settings.metric_rollups.retention_days} days")

    # Test cutoff date calculation
    print("\n--- Cutoff Date Calculation ---")
    policy = RetentionPolicy(data_type="test", retention_days=30)
    cutoff = policy.get_cutoff_date()
    if cutoff:
        print(f"Retention days: {policy.retention_days}")
        print(f"Cutoff date: {cutoff.isoformat()}")
        print(f"Records older than this are eligible for cleanup")

    # Test eligibility check
    print("\n--- Eligibility Check ---")
    old_record_date = datetime.now(UTC) - timedelta(days=45)
    recent_record_date = datetime.now(UTC) - timedelta(days=15)
    print(f"Record from 45 days ago: eligible={policy.is_eligible_for_cleanup(old_record_date)}")
    print(f"Record from 15 days ago: eligible={policy.is_eligible_for_cleanup(recent_record_date)}")

    # Test policy lookup
    print("\n--- Policy Lookup by Data Type ---")
    session_policy = settings.get_policy("sessions")
    if session_policy:
        print(f"Found policy for 'sessions': {session_policy.retention_days} days retention")

    unknown_policy = settings.get_policy("unknown_type")
    print(f"Policy for 'unknown_type': {unknown_policy}")


def main() -> None:
    """Run all demos."""
    print("\n" + "=" * 60)
    print("SECURITY FEATURES DEMONSTRATION")
    print("=" * 60)

    demo_redaction()
    demo_content_capture()
    demo_retention()

    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nKey Takeaways:")
    print("1. Secrets are automatically redacted from logs and exports")
    print("2. Content capture is OFF by default (explicit opt-in required)")
    print("3. Retention policies are configurable per data type")
    print("4. Cutoff dates and eligibility checks are deterministic")
    print("=" * 60)


if __name__ == "__main__":
    main()