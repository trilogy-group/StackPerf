## Codex Workpad - COE-306

```text
macos:/Users/magos/.opensymphony/workspaces/COE-306@d94e95e
```

**Issue:** COE-306 - Build LiteLLM collection job for raw request records and correlation keys
**Issue ID:** ff8c37dc-4abb-4153-a625-40a15d20a873
**Branch:** COE-306-litellm-collection
**Status:** In Progress

### Plan

- [ ] 1. Pull skill execution
  - [x] 1.1 Fetch origin/main
  - [x] 1.2 Verify clean sync (d94e95e)
  - [x] 1.3 Create feature branch COE-306-litellm-collection
- [ ] 2. Build LiteLLM collection job
  - [ ] 2.1 Implement raw request record collection from LiteLLM API
  - [ ] 2.2 Add idempotent ingest cursor/watermark tracking
  - [ ] 2.3 Implement session correlation key preservation
  - [ ] 2.4 Add collection diagnostics for missing fields
- [ ] 3. Update benchmark_core services
  - [ ] 3.1 Add collection job service in benchmark_core/services/
- [ ] 4. Validation and testing
  - [ ] 4.1 Run existing tests
  - [ ] 4.2 Add unit tests for collection job
  - [ ] 4.3 Verify idempotent behavior
- [ ] 5. Documentation and completion
  - [ ] 5.1 Commit changes
  - [ ] 5.2 Push branch

### Acceptance Criteria

- [ ] Collector ingests raw request records without duplication
- [ ] Collected rows preserve session correlation keys when present
- [ ] Collector exposes clear diagnostics for missing fields

### Validation

- [ ] `pytest tests/unit/test_collectors.py -v`
- [ ] New tests for collection job pass

### Notes

- **2025-03-26**: Started implementation. Linear tool not available via CLI - blocker for state transitions.
- **Pull skill evidence**: origin/main merged cleanly, HEAD at d94e95e (grafted).
- Existing litellm_collector.py is a placeholder - needs full implementation.
- Database schema already supports Request model with session_id correlation.

### Blockers

1. **Linear MCP/GraphQL tool unavailable**: Cannot transition issue state via API. Manual state transition required.
   - Issue should move from `Todo` -> `In Progress`
   - Workpad comment cannot be posted to Linear automatically

### Confusions

- None currently
