## Codex Workpad - COE-307

```text
devhost:/Users/magos/.opensymphony/workspaces/COE-307@0c4cebf
```

**Branch**: `COE-307-normalize-requests` (pushed to origin)
**PR**: https://github.com/trilogy-group/StackPerf/pull/20
**Status**: Human Review - PR Created, Awaiting Approval
**Latest Commit**: `0c4cebf`

### Plan

- [x] 1. Analyze existing normalization code
  - [x] 1.1 Review litellm_collector.py - has normalize_request() method
  - [x] 1.2 Review normalization.py - has stub NormalizationJob
  - [x] 1.3 Review request_repository.py - has create_many() for idempotent writes
  - [x] 1.4 Review tests in test_collectors.py
- [x] 2. Create request normalizer job
  - [x] 2.1 Create normalize_requests.py module
  - [x] 2.2 Implement RequestNormalizerJob class
  - [x] 2.3 Integrate with LiteLLMCollector's normalize_request() logic
  - [x] 2.4 Add proper error handling and diagnostics
- [x] 3. Implement normalized request write path
  - [x] 3.1 Ensure idempotent bulk insert via RequestRepository
  - [x] 3.2 Add session correlation validation
  - [x] 3.3 Handle variant_id and experiment_id in metadata
- [x] 4. Create reconciliation report for unmapped rows
  - [x] 4.1 Implement UnmappedRowDiagnostics dataclass
  - [x] 4.2 Track missing fields with counts
  - [x] 4.3 Generate actionable diagnostics
  - [x] 4.4 Add report output methods (JSON, markdown)
- [x] 5. Add CLI commands
  - [x] 5.1 Create normalize command group
  - [x] 5.2 Add run command to execute normalization job
  - [x] 5.3 Add report command to show reconciliation
- [x] 6. Update tests
  - [x] 6.1 Add tests for RequestNormalizerJob (30 tests)
  - [x] 6.2 Add tests for reconciliation reporting
  - [x] 6.3 Run full test suite (240 tests passing)
- [x] 7. Sync and push
  - [x] 7.1 Sync with origin/main (clean, no conflicts)
  - [x] 7.2 Push branch to origin
  - [x] 7.3 Create PR #20
  - [x] 7.4 Add labels (`symphony`, `review-this`)

### Acceptance Criteria

- [x] Normalized requests contain required canonical fields
  - [x] request_id (required, from LiteLLM)
  - [x] session_id (required, FK to sessions)
  - [x] provider (required, from raw.user or raw.customer_identifier)
  - [x] model (required, from raw.model)
  - [x] timestamp (required, from raw.startTime)
  - [x] latency_ms (optional)
  - [x] ttft_ms (optional)
  - [x] tokens_prompt (optional)
  - [x] tokens_completion (optional)
  - [x] error (boolean)
  - [x] error_message (optional)
  - [x] cache_hit (optional)
  - [x] metadata (JSON with correlation keys)
- [x] Requests join cleanly to sessions and variants
  - [x] session_id FK constraint validated
  - [x] variant_id tracked in metadata
  - [x] experiment_id tracked in metadata
- [x] Unmapped rows are surfaced with actionable diagnostics
  - [x] Missing field counts reported
  - [x] Error messages captured
  - [x] Row-level diagnostics available

### Validation

- [x] targeted tests: `python -m pytest tests/unit/test_normalize_requests.py -v`
  - 30/30 tests passing
- [x] full test suite: `python -m pytest tests/ -v`
  - 240/240 tests passing (210 existing + 30 new)
- [x] lint: `ruff check src/collectors/normalize_requests.py src/cli/commands/normalize.py`
  - All checks passed

### Notes

**2025-03-27 02:20**: Created branch COE-307-normalize-requests from main (ad3410e)
**Existing code analysis**:
- litellm_collector.py has comprehensive normalize_request() method (lines 208-353)
- normalization.py has stub NormalizationJob._normalize() returning None (line 38)
- RequestRepository has full idempotent create_many() implementation
- Tests already exist for collector normalization

**Implementation approach**:
1. Create new normalize_requests.py with RequestNormalizerJob
2. Move normalization logic from collector to shared module
3. Add reconciliation reporting
4. Wire into CLI

**PR Created**:
- PR #20: https://github.com/trilogy-group/StackPerf/pull/20
- Labels: `symphony`, `review-this`
- Status: Awaiting human review

### Confusions

