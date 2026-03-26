## Codex Workpad - COE-306

```text
macos:/Users/magos/.opensymphony/workspaces/COE-306@4c31403
```

**Issue:** COE-306 - Build LiteLLM collection job for raw request records and correlation keys
**Issue ID:** ff8c37dc-4abb-4153-a625-40a15d20a873
**Branch:** COE-306-litellm-collection
**Status:** In Progress → Human Review (BLOCKED: GitHub PAT permissions)

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

- **2025-03-26 (Retry #4)**: Continuation session. Implementation complete and validated. PR creation still blocked by PAT permissions.
- **Commits**:
  - 4c31403 - COE-306: Retry #4 - Update workpad with retry status (current)
  - 4feaa31 - COE-306: Retry #3 - Update workpad with PR creation blocker status
  - 4a1d54d - COE-306: Final workpad - correct HEAD commit hash
  - ff092d4 - COE-306: Final workpad - document complete blockers status
  - 3638617 - COE-306: Update workpad for retry #2 - document PR creation blocker
  - 87eb869 - COE-306: Build LiteLLM collection job for raw request records and correlation keys (main implementation)
- **Tests**: All 100 unit tests passing, including 29 collector-specific tests (verified in Retry #4)
- **Branch**: `COE-306-litellm-collection` pushed to origin (4c31403)
- **GitHub PR**: **BLOCKED - Retry #4 Confirmed** - GitHub PAT lacks write permissions
  - Commands attempted:
    - `gh pr create --title ... --body ... --base main` (interactive prompt timeout)
    - `gh pr create --repo trilogy-group/StackPerf --head COE-306-litellm-collection --base main` (failed)
    - Direct GitHub REST API call: `curl -X POST /repos/trilogy-group/StackPerf/pulls` (403 Forbidden)
  - Error: `{"message":"Resource not accessible by personal access token","status":"403"}`
  - Token scopes: 'admin:public_key', 'gist', 'read:org', 'repo'
  - Root cause: Fine-grained PAT lacks explicit `pull_requests:write` permission on trilogy-group/StackPerf repository

### Blockers

1. **GitHub PR Creation**: **ACTIVE - Retry #4 Confirmed PAT Permission Issue**
   - **Status**: Still blocked after retry #4. GitHub API returns 403 Forbidden.
   - **Error**: `{"message":"Resource not accessible by personal access token","status":"403"}`
   - **Token analysis**: GH_TOKEN has 'repo' scope but fine-grained PAT requires explicit repository-level permissions
   - **Root cause**: The fine-grained PAT needs `pull_requests:write` permission explicitly granted on the trilogy-group/StackPerf repository
   - **Fallback strategies attempted in Retry #4**:
     - Non-interactive `gh pr create` (fails with interactive prompt)
     - Direct GitHub REST API call with curl (403 Forbidden)
     - All fallback strategies exhausted
   - **Impact**: Cannot create PR programmatically; blocks transition to Human Review
   - **Action required**: Human must create PR via GitHub UI
     - Branch: `COE-306-litellm-collection` (commit 4c31403, ahead of main)
     - Compare URL: https://github.com/trilogy-group/StackPerf/compare/main...COE-306-litellm-collection
     - PR Title: "COE-306: Build LiteLLM collection job for raw request records and correlation keys"
     - Description: See WORKPAD.md "Implementation Summary" section below
     - Labels to add: `symphony`, `review-this`
   - **Resolution path**: Classic PAT with full `repo` access OR update fine-grained PAT with explicit `pull_requests:write` permission on trilogy-group/StackPerf

2. **Linear API**: **UNAVAILABLE - `linear_graphql` tool not configured**
   - **Status**: No Linear MCP server or `linear_graphql` tool available in session
   - **Impact**: Cannot query/update Linear issue programmatically
   - **Action required**: Human must manually:
     - Verify issue is in "In Progress" state
     - Transition issue from "In Progress" to "Human Review" after PR is created
     - Attach PR URL to Linear issue

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
