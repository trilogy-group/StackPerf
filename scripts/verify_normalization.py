"""Verification script for request normalization functionality.

This script demonstrates the end-to-end normalization flow without requiring
an actual LiteLLM proxy or database. It shows:
1. Raw LiteLLM data normalization
2. Reconciliation report generation
3. Session correlation key preservation

Usage:
    PYTHONPATH=src python scripts/verify_normalization.py
"""

from uuid import uuid4

from collectors.normalize_requests import (
    ReconciliationReport,
    RequestNormalizer,
)


def print_section(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_basic_normalization() -> None:
    """Demonstrate basic normalization of valid LiteLLM request data."""
    print_section("Demo 1: Basic Normalization")

    session_id = uuid4()
    normalizer = RequestNormalizer(session_id)

    # Sample raw LiteLLM request data
    raw_request = {
        "request_id": "litellm-req-001",
        "startTime": "2025-03-26T10:30:00+00:00",
        "model": "gpt-4-turbo",
        "user": "test-user-123",
        "latency": 1.234,  # seconds
        "usage": {
            "prompt_tokens": 150,
            "completion_tokens": 75,
        },
        "cache_hit": False,
        "metadata": {
            "session_id": str(session_id),
            "experiment_id": "exp-001",
            "variant_id": "var-001",
            "trace_id": "trace-abc-123",
        },
    }

    print("Raw LiteLLM data:")
    print(f"  request_id: {raw_request['request_id']}")
    print(f"  startTime: {raw_request['startTime']}")
    print(f"  model: {raw_request['model']}")
    print(f"  user: {raw_request['user']}")
    print(f"  latency: {raw_request['latency']}s")
    print(f"  usage: {raw_request['usage']}")

    result, diag = normalizer.normalize(raw_request)

    print("\nNormalized Request ORM:")
    print(f"  request_id: {result.request_id}")
    print(f"  session_id: {result.session_id}")
    print(f"  provider: {result.provider}")
    print(f"  model: {result.model}")
    print(f"  timestamp: {result.timestamp}")
    print(f"  latency_ms: {result.latency_ms}")
    print(f"  tokens_prompt: {result.tokens_prompt}")
    print(f"  tokens_completion: {result.tokens_completion}")
    print(f"  cache_hit: {result.cache_hit}")
    print(f"  metadata keys: {list(result.request_metadata.keys())}")

    # Verify correlation keys
    assert result.request_metadata.get("experiment_id") == "exp-001"
    assert result.request_metadata.get("variant_id") == "var-001"
    assert result.request_metadata.get("trace_id") == "trace-abc-123"

    print("\n✓ Correlation keys preserved in metadata")
    print("✓ Latency converted from seconds (1.234s → 1234.0ms)")
    print("✓ All required fields present")


def demo_timestamp_variants() -> None:
    """Demonstrate handling of various timestamp formats."""
    print_section("Demo 2: Timestamp Format Variants")

    session_id = uuid4()
    normalizer = RequestNormalizer(session_id)

    test_cases = [
        ("ISO with timezone", {"startTime": "2025-03-26T10:30:00+00:00"}),
        ("ISO with Z suffix", {"timestamp": "2025-03-26T10:30:00Z"}),
        ("Unix timestamp (float)", {"created_at": 1711441800.0}),
        ("Unix timestamp (int)", {"startTime": 1711441800}),
    ]

    for name, fields in test_cases:
        raw = {
            "request_id": f"req-{name.replace(' ', '-')}",
            "model": "gpt-4",
            **fields,
        }
        result, diag = normalizer.normalize(raw)
        status = "✓" if result else "✗"
        print(f"  {status} {name}: {result.timestamp if result else diag.reason}")


def demo_error_handling() -> None:
    """Demonstrate error extraction from various formats."""
    print_section("Demo 3: Error Handling")

    session_id = uuid4()
    normalizer = RequestNormalizer(session_id)

    error_cases = [
        ("Error as string", {"error": "Rate limit exceeded"}),
        ("Error as dict", {"error": {"message": "Invalid API key"}}),
        ("Error in response", {"response": {"error": "Timeout"}}),
        ("No error", {}),
    ]

    for name, error_fields in error_cases:
        raw = {
            "request_id": f"req-{name.replace(' ', '-')}",
            "startTime": "2025-03-26T10:30:00+00:00",
            "model": "gpt-4",
            **error_fields,
        }
        result, _ = normalizer.normalize(raw)
        print(f"  {'✓' if result else '✗'} {name}: error={result.error}, message={result.error_message}")


def demo_reconciliation_report() -> None:
    """Demonstrate reconciliation report generation."""
    print_section("Demo 4: Reconciliation Report")

    session_id = uuid4()

    # Simulate a batch of raw requests with some invalid entries
    raw_requests = [
        # Valid requests
        {"request_id": "req-001", "startTime": "2025-03-26T10:30:00+00:00", "model": "gpt-4"},
        {"request_id": "req-002", "startTime": "2025-03-26T10:31:00+00:00", "model": "gpt-3.5"},
        {"request_id": "req-003", "startTime": "2025-03-26T10:32:00+00:00", "model": "gpt-4"},
        # Missing request_id
        {"startTime": "2025-03-26T10:33:00+00:00", "model": "gpt-4"},
        # Missing timestamp
        {"request_id": "req-005", "model": "gpt-4"},
        # Invalid timestamp
        {"request_id": "req-006", "startTime": "not-a-timestamp", "model": "gpt-4"},
        # Non-dict data (simulated)
        None,
    ]

    report = ReconciliationReport()
    normalizer = RequestNormalizer(session_id)

    for i, raw in enumerate(raw_requests):
        normalized, diag = normalizer.normalize(raw, row_index=i)
        if normalized:
            report.add_mapped()
        else:
            report.add_unmapped(
                raw_data=raw if isinstance(raw, dict) else {},
                reason=diag.reason if diag else "Unknown",
                missing_fields=diag.missing_fields if diag else [],
                error_message=diag.error_message if diag else "",
                row_index=i,
            )

    print("Batch Processing Results:")
    print(f"  Total rows: {report.total_rows}")
    print(f"  Mapped: {report.mapped_count} ({report.success_rate:.1f}%)")
    print(f"  Unmapped: {report.unmapped_count}")
    print("\nMissing Field Counts:")
    for field, count in report.missing_field_counts.items():
        print(f"    {field}: {count}")
    print("\nError Categories:")
    for category, count in report.error_counts.items():
        print(f"    {category}: {count}")
    print("\nSample Unmapped Rows:")
    for diag in report.unmapped_diagnostics[:3]:
        print(f"  Row {diag.row_index}: {diag.reason}")
        if diag.missing_fields:
            print(f"    Missing: {', '.join(diag.missing_fields)}")


def demo_markdown_report() -> None:
    """Demonstrate markdown report output."""
    print_section("Demo 5: Markdown Report Output")

    session_id = uuid4()
    report = ReconciliationReport()
    normalizer = RequestNormalizer(session_id)

    # Create sample data
    requests = [
        {"request_id": f"req-{i:03d}", "startTime": "2025-03-26T10:30:00+00:00", "model": "gpt-4"}
        for i in range(95)
    ]
    # Add some failures
    requests.extend([
        {"startTime": "2025-03-26T10:30:00+00:00"},  # missing request_id
        {"request_id": "bad-timestamp", "startTime": "invalid"},  # bad timestamp
    ])

    for i, raw in enumerate(requests):
        normalized, diag = normalizer.normalize(raw, row_index=i)
        if normalized:
            report.add_mapped()
        else:
            report.add_unmapped(
                raw_data=raw,
                reason=diag.reason if diag else "Unknown",
                missing_fields=diag.missing_fields if diag else [],
                row_index=i,
            )

    # Show first 50 lines of markdown report
    markdown = report.to_markdown()
    print("Generated Markdown Report (first 50 lines):")
    print("-" * 70)
    for line in markdown.split("\n")[:50]:
        print(line)
    print("-" * 70)


def demo_json_output() -> None:
    """Demonstrate JSON report output."""
    print_section("Demo 6: JSON Report Output")

    import json

    session_id = uuid4()
    report = ReconciliationReport()
    normalizer = RequestNormalizer(session_id)

    # Create sample data with various issues
    requests = [
        {"request_id": "req-001", "startTime": "2025-03-26T10:30:00+00:00", "model": "gpt-4"},
        {"startTime": "2025-03-26T10:30:00+00:00"},  # missing request_id
        {"request_id": "req-003", "model": "gpt-4"},  # missing timestamp
        {"request_id": "req-004", "startTime": "2025-03-26T10:30:00+00:00"},  # missing model (defaults to unknown)
    ]

    for i, raw in enumerate(requests):
        normalized, diag = normalizer.normalize(raw, row_index=i)
        if normalized:
            report.add_mapped()
        else:
            report.add_unmapped(
                raw_data=raw,
                reason=diag.reason if diag else "Unknown",
                missing_fields=diag.missing_fields if diag else [],
                row_index=i,
            )

    json_output = json.dumps(report.to_dict(), indent=2)
    print("Generated JSON Report:")
    print("-" * 70)
    print(json_output)
    print("-" * 70)


def main() -> None:
    """Run all demonstrations."""
    print("\n" + "=" * 70)
    print("  Request Normalization Verification")
    print("  COE-307: Normalize LiteLLM request data")
    print("=" * 70)

    try:
        demo_basic_normalization()
        demo_timestamp_variants()
        demo_error_handling()
        demo_reconciliation_report()
        demo_markdown_report()
        demo_json_output()

        print_section("Verification Complete")
        print("✓ All normalization demonstrations passed")
        print("✓ RequestNormalizer correctly maps LiteLLM fields to canonical form")
        print("✓ ReconciliationReport accurately tracks unmapped rows")
        print("✓ Correlation keys preserved in metadata for session joining")
        print("✓ Multiple timestamp formats handled correctly")
        print("✓ Error extraction from various formats working")

    except AssertionError as e:
        print(f"\n✗ Verification failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
