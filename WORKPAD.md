## Codex Workpad - COE-306

```text
macos:/Users/magos/.opensymphony/workspaces/COE-306@c083393
```

**Issue:** COE-306 - Build LiteLLM collection job for raw request records and correlation keys
**Issue ID:** ff8c37dc-4abb-4153-a625-40a15d20a873
**Branch:** COE-306-litellm-collection
**Status:** In Progress → Human Review (PR #14 Created Successfully)

### Plan

- [x] 1. Pull skill execution
  - [x] 1.1 Fetch origin/main
  - [x] 1.2 Verify clean sync (d94e95e)
  - [x] 1.3 Create feature branch COE-306-litellm-collection
- [x] 2. Build LiteLLM collection job
  - [x] 2.1 Implement raw request record collection from LiteLLM API
  - [x] 2.2 Add idempotent ingest cursor/watermark tracking (IngestWatermark class)
  - [x] 2.3 Implement session correlation key preservation (correlation_keys in normalize_request)
  - [x] 2.4 Add collection diagnostics for missing fields (CollectionDiagnostics class)
- [x] 3. Update benchmark_core services
  - [x] 3.1 Add CollectionJobService in benchmark_core/services.py
- [x] 4. Validation and testing
  - [x] 4.1 Run existing tests (100 passed)
  - [x] 4.2 Add unit tests for collection job (29 tests in test_collectors.py)
  - [x] 4.3 Verify idempotent behavior (watermark resumption tests)
- [x] 5. Documentation and completion
  - [x] 5.1 Commit changes (87eb869)
  - [x] 5.2 Push branch (COE-306-litellm-collection)
- [x] 6. PR Creation (COMPLETED - Session #8)
  - [x] 6.1 Create PR via GitHub CLI - SUCCESS: https://github.com/trilogy-group/StackPerf/pull/14
  - [x] 6.2 Add `symphony` and `review-this` labels - SUCCESS (both labels applied)

### Acceptance Criteria

- [x] Collector ingests raw request records without duplication
  - Idempotent via `IngestWatermark` cursor tracking
  - Repository `create_many` handles duplicate request_id gracefully
- [x] Collected rows preserve session correlation keys when present
  - Correlation keys preserved in metadata: session_id, experiment_id, variant_id, task_card_id, harness_profile, trace_id, span_id, parent_span_id
- [x] Collector exposes clear diagnostics for missing fields
  - `CollectionDiagnostics` tracks missing_fields counts and errors
  - `CollectionJobService.get_diagnostics_summary()` provides human-readable summary

### Validation

- [x] `pytest tests/unit/test_collectors.py -v` - 29 passed
- [x] `pytest tests/unit/ -v` - 100 passed
- [x] Specific tests:
  - `test_normalize_request_correlation_keys_preserved` - Verifies session_id, experiment_id in metadata
  - `test_collection_diagnostics_record_missing_field` - Verifies missing field tracking
  - `test_collect_requests_idempotent_insert` - Verifies watermark-based idempotency
  - `test_collection_job_service_diagnostics_summary` - Verifies diagnostics summary output

### Implementation Details

**src/collectors/litellm_collector.py:**
- `CollectionDiagnostics` - Tracks total_raw_records, normalized_count, skipped_count, missing_fields dict, errors list
- `IngestWatermark` - Serializable cursor with last_request_id, last_timestamp, record_count
- `LiteLLMCollector.collect_requests()` - Async collection with watermark resumption
- `LiteLLMCollector.normalize_request()` - Normalizes LiteLLM spend logs to Request model

**src/benchmark_core/services.py:**
- `CollectionJobService.run_collection_job()` - Orchestrates collection with time window support
- `CollectionJobService.run_collection_job_with_window()` - Automatic lookback window
- `CollectionJobService.get_diagnostics_summary()` - Human-readable diagnostics

### Notes

- **2025-03-26 (Session #8 - SUCCESS)**: PR successfully created! Using `gh pr create` via CLI worked with GH_TOKEN.
  - PR #14: https://github.com/trilogy-group/StackPerf/pull/14
  - Labels added: `symphony`, `review-this`
  - AI PR review triggered via `review-this` label
  - **Current HEAD**: b5936b3 (19 commits ahead of main including workpad updates)
  - **Status**: Ready for Human Review - all acceptance criteria met
- **2025-03-26 (Retry #7 - BLOCKED)**: Fresh session after LLM provider settings changed. PAT permissions CONFIRMED BLOCKING.
  - GitHub REST API test: `POST /repos/trilogy-group/StackPerf/pulls` → 403
  - Error: `{"message":"Resource not accessible by personal access token","status":"403"}`
- **2025-03-26 (Retry #6)**: Continuation session after LLM provider change. Retried PR creation - **PAT permissions still blocking**.
- **2025-03-26 (Retry #4-5)**: Continuation sessions. Implementation complete and validated. PR creation blocked by PAT permissions. All fallback strategies exhausted.
- **Tests**: All 100 unit tests passing, including 29 collector-specific tests
- **Branch**: `COE-306-litellm-collection` pushed to origin

### Blockers

**ALL BLOCKERS RESOLVED - Session #8**

1. **GitHub PR Creation**: ✅ **RESOLVED** (Session #8)
   - **Status**: PR #14 successfully created using `gh pr create` with GH_TOKEN environment variable
   - **PR URL**: https://github.com/trilogy-group/StackPerf/pull/14
   - **Resolution**: Using `gh` CLI instead of direct REST API worked correctly
   - **Labels applied**: `symphony`, `review-this`

2. **Linear API**: **UNAVAILABLE - No MCP/tool configured**
   - **Status**: No Linear MCP server or `linear_graphql` tool available
   - **Impact**: Cannot query/update Linear issue programmatically
   - **Action required**: Human must manually:
     - Transition issue from "In Progress" to "Human Review"
     - Attach PR #14 URL to Linear issue: https://github.com/trilogy-group/StackPerf/pull/14

### Implementation Summary

**Files Modified:**
- `src/collectors/litellm_collector.py` - New implementation with CollectionDiagnostics, IngestWatermark, LiteLLMCollector
- `src/benchmark_core/services.py` - Added CollectionJobService
- `tests/unit/test_collectors.py` - 29 comprehensive unit tests

**Key Features:**
1. **Raw Collection Job**: Async collection from LiteLLM API with spend logs endpoint
2. **Idempotent Ingest**: IngestWatermark tracks last_request_id, last_timestamp, record_count for resumption
3. **Correlation Keys**: Preserves session_id, experiment_id, variant_id, task_card_id, harness_profile, trace_id, span_id, parent_span_id in metadata
4. **Diagnostics**: CollectionDiagnostics tracks missing_fields, errors, skipped_count for observability

### Confusions

None currently
