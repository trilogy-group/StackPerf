#!/usr/bin/env python3
"""Demo script showing LiteLLM collector functionality.

This script demonstrates the collector working end-to-end with mock data,
showing:
- Collection diagnostics
- Watermark tracking
- Correlation key preservation
"""

import asyncio

# Set up path for imports
import sys
from datetime import UTC, datetime
from uuid import uuid4

sys.path.insert(0, "src")

from benchmark_core.models import Request
from benchmark_core.services import CollectionJobService
from collectors.litellm_collector import (
    CollectionDiagnostics,
    IngestWatermark,
)


class MockRepository:
    """Mock repository for demo purposes."""

    def __init__(self):
        self.requests = []

    async def create_many(self, requests: list[Request]) -> list[Request]:
        """Simulate bulk insert - handles deduplication."""
        existing_ids = {r.request_id for r in self.requests}
        new_requests = [r for r in requests if r.request_id not in existing_ids]
        self.requests.extend(new_requests)
        return new_requests


async def demo_collector():
    """Demonstrate collector functionality."""
    print("=" * 60)
    print("LiteLLM Collector Demo")
    print("=" * 60)

    # Create mock repository
    repo = MockRepository()

    # Create service
    service = CollectionJobService(
        litellm_base_url="http://localhost:4000",
        litellm_api_key="demo-key",
        repository=repo,
    )

    session_id = uuid4()
    print(f"\nSession ID: {session_id}")

    # Mock raw LiteLLM data (simulating what the API would return)
    mock_raw_data = [
        {
            "request_id": "req-001",
            "startTime": datetime.now(UTC).isoformat(),
            "model": "gpt-4",
            "user": "test-user",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "session_id": "sess-123",
            "experiment_id": "exp-456",
            "variant_id": "var-789",
            "trace_id": "trace-abc",
        },
        {
            "request_id": "req-002",
            "startTime": datetime.now(UTC).isoformat(),
            "model": "claude-3",
            "user": "test-user",
            "usage": {"prompt_tokens": 200, "completion_tokens": 100},
            "session_id": "sess-123",
            "experiment_id": "exp-456",
            "task_card_id": "task-xyz",
            "span_id": "span-def",
        },
        {
            "request_id": "req-003",
            "startTime": datetime.now(UTC).isoformat(),
            "model": "gpt-3.5",
            "user": "test-user",
            # Missing some fields to demonstrate diagnostics
        },
    ]

    print("\n--- Testing Normalization ---")
    diagnostics = CollectionDiagnostics()
    collector = service._collector

    normalized_requests = []
    for raw in mock_raw_data:
        req = collector.normalize_request(raw, session_id, diagnostics)
        if req:
            normalized_requests.append(req)
            print(f"✓ Normalized: {req.request_id}")
            print(f"  - Model: {req.model}, Provider: {req.provider}")
            print(f"  - Tokens: {req.tokens_prompt}/{req.tokens_completion}")
            print(f"  - Metadata keys: {list(req.metadata.keys())}")
        else:
            print(f"✗ Skipped: {raw.get('request_id', 'unknown')}")

    print("\n--- Diagnostics Summary ---")
    print(f"Total raw records processed: {len(mock_raw_data)}")
    print(f"Successfully normalized: {len(normalized_requests)}")
    print(f"Skipped: {diagnostics.skipped_count}")

    if diagnostics.missing_fields:
        print("\nMissing fields detected:")
        for field, count in diagnostics.missing_fields.items():
            print(f"  - {field}: {count} occurrences")

    print("\n--- Testing Watermark ---")
    watermark = IngestWatermark(
        last_request_id="req-002",
        last_timestamp=datetime.now(UTC),
        record_count=2,
    )
    print(f"Created watermark: {watermark.to_dict()}")

    # Roundtrip test
    watermark_dict = watermark.to_dict()
    restored = IngestWatermark.from_dict(watermark_dict)
    print(f"Restored watermark: {restored.to_dict()}")
    print(f"Roundtrip successful: {watermark_dict == restored.to_dict()}")

    print("\n--- Correlation Keys Preserved ---")
    for req in normalized_requests:
        correlation_keys = {k: v for k, v in req.metadata.items() if k not in ["litellm_raw_keys"]}
        if correlation_keys:
            print(f"\nRequest {req.request_id}:")
            for key, value in correlation_keys.items():
                print(f"  - {key}: {value}")

    print("\n--- Testing Idempotent Insert ---")
    # First insert
    result1 = await repo.create_many(normalized_requests)
    print(f"First insert: {len(result1)} new records")

    # Second insert (same data - should be deduplicated)
    result2 = await repo.create_many(normalized_requests)
    print(f"Second insert: {len(result2)} new records (idempotent)")

    print(f"\nTotal in repository: {len(repo.requests)} records")

    print("\n--- Collection Job Result Structure ---")
    # Simulate a job result
    result = await service.run_collection_job(session_id=session_id)
    print(f"Success: {result.success}")
    print(f"Requests collected: {result.requests_collected}")
    print(f"Requests normalized: {result.requests_normalized}")
    print(f"Watermark: {result.watermark.to_dict()}")

    if result.diagnostics:
        summary = service.get_diagnostics_summary(result.diagnostics)
        print(f"\nDiagnostics summary keys: {list(summary.keys())}")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_collector())
