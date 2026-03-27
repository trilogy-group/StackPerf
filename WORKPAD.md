## Codex Workpad - COE-306

```text
macos:/Users/magos/.opensymphony/workspaces/COE-306@9486904
```

**Issue:** COE-306 - Build LiteLLM collection job for raw request records and correlation keys
**Issue ID:** ff8c37dc-4abb-4153-a625-40a15d20a873
**Branch:** COE-306-litellm-collection
**Status:** In Progress → Human Review (BLOCKED: GitHub PAT permissions - Retry #7 Confirmed)

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
- [ ] 6. PR Creation (BLOCKED - PAT Permissions)
  - [ ] 6.1 Create PR via GitHub API (blocked: needs pull_requests:write permission)
  - [ ] 6.2 Add `symphony` and `review-this` labels

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

- **2025-03-26 (Retry #7 - FINAL)**: Fresh session after LLM provider settings changed. Final attempt to create PR - **PAT permissions CONFIRMED BLOCKING**.
  - GitHub REST API test: `POST /repos/trilogy-group/StackPerf/pulls` → 403
  - Error: `{"message":"Resource not accessible by personal access token","status":"403"}`
  - Read access confirmed: `GET /repos/trilogy-group/StackPerf` → 200
  - **Root cause confirmed**: Fine-grained PAT lacks `pull_requests:write` permission
  - **All 100 unit tests passing** - implementation complete and validated
  - **Current HEAD**: 9b2b9fd (18 commits ahead of main after workpad update)
  - **Status**: Moving to Human Review with blocker documentation
- **2025-03-26 (Retry #6)**: Continuation session after LLM provider change. Retried PR creation - **PAT permissions still blocking**.
  - `gh pr create` via CLI: GraphQL "Resource not accessible by personal access token" error
  - Direct GitHub REST API: Connection timed out
  - **Retry #6 confirmed**: Token scopes are 'repo' but fine-grained PAT lacks explicit `pull_requests:write` on trilogy-group/StackPerf
  - **Commits**:
    - 8baee38 - COE-306: Retry #6 - Updated workpad with retry #6 blocker status (current)
    - f557306 - COE-306: Retry #6 - Document PR creation blocker status after LLM provider change
    - f0ca669 - COE-306: Final workpad - ready for manual PR creation
- **2025-03-26 (Retry #4-5)**: Continuation sessions. Implementation complete and validated. PR creation blocked by PAT permissions. All fallback strategies exhausted.
  - 5fb3708 - COE-306: Final retry #4 workpad - confirmed PAT permission blocker
  - 4c31403 - COE-306: Retry #4 - Update workpad with retry status
  - 4feaa31 - COE-306: Retry #3 - Update workpad with PR creation blocker status
  - 4a1d54d - COE-306: Final workpad - correct HEAD commit hash
  - ff092d4 - COE-306: Final workpad - document complete blockers status
  - 3638617 - COE-306: Update workpad for retry #2 - document PR creation blocker
  - 87eb869 - COE-306: Build LiteLLM collection job for raw request records and correlation keys (main implementation)
- **Tests**: All 100 unit tests passing, including 29 collector-specific tests (verified in Retry #4-7)
- **Branch**: `COE-306-litellm-collection` pushed to origin (9486904)

### Blockers

1. **GitHub PR Creation**: **FINAL CONFIRMATION - PAT Permission Issue Blocking**
   - **Status**: Confirmed after retry #7. GitHub REST API returns 403.
   - **Error**: `{"message":"Resource not accessible by personal access token","status":"403"}`
   - **Root cause**: Fine-grained PAT has `repo` scope but lacks explicit `pull_requests:write` permission on trilogy-group/StackPerf repository
   - **Evidence**:
     - `GET /repos/trilogy-group/StackPerf` → 200 (read access works)
     - `POST /repos/trilogy-group/StackPerf/pulls` → 403 (write access denied)
   - **Impact**: Cannot create PR programmatically; moving to Human Review with blocker note
   - **Action required**: Human must create PR via GitHub UI
     - Branch: `COE-306-litellm-collection` (commit 9b2b9fd, 18 commits ahead of main)
     - Compare URL: https://github.com/trilogy-group/StackPerf/compare/main...COE-306-litellm-collection
     - PR Title: "COE-306: Build LiteLLM collection job for raw request records and correlation keys"
     - Description: Use PR_DESCRIPTION.md (ready in repo root)
     - Labels to add: `symphony`, `review-this`
   - **Resolution path**: Update fine-grained PAT with `pull_requests:write` permission on trilogy-group/StackPerf OR use classic PAT with full `repo` scope

2. **Linear API**: **UNAVAILABLE - No MCP/tool configured**
   - **Status**: No Linear MCP server or `linear_graphql` tool available
   - **Impact**: Cannot query/update Linear issue programmatically
   - **Action required**: Human must manually:
     - Transition issue from "In Progress" to "Human Review"
     - Attach PR URL to Linear issue once created

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
