## Codex Workpad - COE-306

```text
macos:/Users/magos/.opensymphony/workspaces/COE-306@5e42103
```

**Issue:** COE-306 - Build LiteLLM collection job for raw request records and correlation keys
**Issue ID:** ff8c37dc-4abb-4153-a625-40a15d20a873
**Branch:** COE-306-litellm-collection
**Status:** In Progress → Human Review (BLOCKED: PR creation)

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

- **2025-03-26 (Retry #1)**: Continuation session. Implementation already complete from previous run.
- **Commits**:
  - 87eb869 - COE-306: Build LiteLLM collection job for raw request records and correlation keys
  - d4f429d - Update workpad: mark all tasks complete, add validation evidence
  - 5e42103 - Update workpad: document GitHub PR blocker
- **Tests**: All 100 unit tests passing, including 29 collector-specific tests
- **Branch**: `COE-306-litellm-collection` pushed to origin (5e42103)
- **Linear API**: Unavailable (GRAPHQL_VALIDATION_FAILED error on previous run)
- **GitHub PR**: FAILED - GH_TOKEN lacks `repo` scope for createPullRequest
  - Attempted: `gh pr create --fill` - Result: "Resource not accessible by personal access token"
  - Token has scopes: 'admin:public_key', 'gist', 'read:org', 'repo' but GraphQL mutation still blocked

### Blockers

1. **GitHub PR Creation**: ACTIVE - GH_TOKEN permissions insufficient for GraphQL mutation
   - **Impact**: Cannot create PR programmatically; blocks transition to Human Review
   - **Token scopes**: 'admin:public_key', 'gist', 'read:org', 'repo' (repo scope present but GraphQL createPullRequest still blocked)
   - **Error**: `GraphQL: Resource not accessible by personal access token (createPullRequest)`
   - **Action required**: Human must create PR via GitHub UI
     - Branch pushed: `COE-306-litellm-collection` (2b84693)
     - Compare URL: https://github.com/trilogy-group/StackPerf/compare/main...COE-306-litellm-collection
     - Add label: `symphony`
     - Add label: `review-this` (for AI PR review)
     - Attach PR to Linear issue COE-306
   - **Alternative**: Grant `repo` scope with write permissions or use classic PAT with full repo access

2. **Linear API**: UNAVAILABLE - Previous error: GRAPHQL_VALIDATION_FAILED on $issueId variable type
   - **Impact**: Cannot update issue state programmatically
   - **Action required**: Human must manually transition issue from "In Progress" to "Human Review" after PR is created

### Confusions

None currently
