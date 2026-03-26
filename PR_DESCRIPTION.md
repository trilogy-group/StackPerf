# COE-306: Build LiteLLM collection job for raw request records and correlation keys

## Summary

This PR implements the LiteLLM collection job for raw request records with correlation key preservation, as specified in COE-306.

## Deliverables

- ✅ Raw collection job from LiteLLM API
- ✅ Idempotent ingest watermark tracking
- ✅ Collection diagnostics for missing fields

## Changes

### src/collectors/litellm_collector.py
- `CollectionDiagnostics` - Tracks total_raw_records, normalized_count, skipped_count, missing_fields dict, errors list
- `IngestWatermark` - Serializable cursor with last_request_id, last_timestamp, record_count
- `LiteLLMCollector.collect_requests()` - Async collection with watermark resumption
- `LiteLLMCollector.normalize_request()` - Normalizes LiteLLM spend logs to Request model

### src/benchmark_core/services.py
- `CollectionJobService.run_collection_job()` - Orchestrates collection with time window support
- `CollectionJobService.get_diagnostics_summary()` - Human-readable diagnostics

## Acceptance Criteria

- ✅ Collector ingests raw request records without duplication (idempotent via IngestWatermark)
- ✅ Collected rows preserve session correlation keys when present (session_id, experiment_id, variant_id, task_card_id, harness_profile, trace_id, span_id, parent_span_id)
- ✅ Collector exposes clear diagnostics for missing fields (CollectionDiagnostics tracks missing_fields counts and errors)

## Testing

- All 100 unit tests passing
- 29 collector-specific tests added in tests/unit/test_collectors.py
- Verified watermark-based idempotency
- Verified correlation key preservation
- Verified diagnostics tracking

## Correlation Keys Preserved

The following session correlation keys are extracted from LiteLLM metadata and preserved in the collected records:

- `session_id` - Session identifier
- `experiment_id` - Experiment identifier
- `variant_id` - Variant identifier
- `task_card_id` - Task card identifier
- `harness_profile` - Harness profile
- `trace_id` - Distributed trace ID
- `span_id` - Span identifier
- `parent_span_id` - Parent span identifier

## Idempotent Ingest

The `IngestWatermark` class provides cursor-based resumption:
- `last_request_id` - Last processed request for deduplication
- `last_timestamp` - Timestamp watermark for incremental collection
- `record_count` - Records processed in last run

Closes COE-306
