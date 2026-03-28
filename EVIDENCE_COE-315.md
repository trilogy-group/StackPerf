# COE-315 Evidence: Structured Export Commands

## Summary

This document provides evidence of the implemented structured export commands for session and experiment data.

## Implementation Evidence

### Export Service

**File**: `src/reporting/export_service.py`

- **Lines 1-50**: ExportService class with canonical field definitions
- **Lines 52-161**: `export_session()` method with canonical fields and redaction
- **Lines 163-236**: `export_experiment()` method with session aggregation
- **Lines 238-298**: Helper methods for formatting and calculations
- **Lines 300-495**: ExportSerializer with JSON, CSV, and Parquet support

### Export CLI Commands

**File**: `src/cli/commands/export.py`

- **Lines 20-111**: Session export command with artifact registration
- **Lines 114-210**: Experiment export command with artifact registration  
- **Lines 213-237**: Comparison command (alias for experiment)

## Test Evidence

### Unit Tests

**File**: `tests/unit/test_export_service.py`

- 12 tests covering ExportService and ExportSerializer
- All tests passing

**File**: `tests/unit/test_export_commands.py`

- 10 tests covering CLI commands
- All tests passing

### Test Execution

```bash
$ python -m pytest tests/unit/test_export_service.py tests/unit/test_export_commands.py -v
============================= test session starts ==============================
platform darwin, Python 3.12.9, pytest-9.0.2, pluggy-1.6.0
tests/unit/test_export_service.py::TestExportService::test_export_session_basic PASSED
tests/unit/test_export_service.py::TestExportService::test_export_session_with_requests PASSED
tests/unit/test_export_service.py::TestExportService::test_export_session_with_secrets PASSED
tests/unit/test_export_service.py::TestExportService::test_export_session_not_found PASSED
tests/unit/test_export_service.py::TestExportService::test_export_experiment_basic PASSED
tests/unit/test_export_service.py::TestExportService::test_export_experiment_with_sessions PASSED
tests/unit/test_export_service.py::TestExportService::test_export_experiment_with_requests PASSED
tests/unit/test_export_service.py::TestExportService::test_export_experiment_not_found PASSED
tests/unit/test_export_service.py::TestExportSerializer::test_to_json PASSED
tests/unit/test_export_service.py::TestExportSerializer::test_to_csv PASSED
tests/unit/test_export_service.py::TestExportSerializer::test_to_csv_empty PASSED
tests/unit/test_export_service.py::TestExportSerializer::test_to_parquet_without_pyarrow PASSED
tests/unit/test_export_commands.py::TestExportSessionCommand::test_export_session_json PASSED
tests/unit/test_export_commands.py::TestExportSessionCommand::test_export_session_csv PASSED
tests/unit/test_export_commands.py::TestExportSessionCommand::test_export_session_with_artifact_registration PASSED
tests/unit/test_export_commands.py::TestExportSessionCommand::test_export_session_invalid_id PASSED
tests/unit/test_export_commands.py::TestExportSessionCommand::test_export_session_no_requests PASSED
tests/unit/test_export_commands.py::TestExportExperimentCommand::test_export_experiment_json PASSED
tests/unit/test_export_commands.py::TestExportExperimentCommand::test_export_experiment_csv PASSED
tests/unit/test_export_commands.py::TestExportExperimentCommand::test_export_experiment_with_requests PASSED
tests/unit/test_export_commands.py::TestExportExperimentCommand::test_export_experiment_with_artifact_registration PASSED
tests/unit/test_export_commands.py::TestExportComparisonCommand::test_comparison_alias PASSED
============================== 22 passed in 0.47s ===============================
```

## CLI Usage Examples

### Session Export

```bash
# Export session to JSON (default)
benchmark export session <session-uuid>

# Export session to CSV with canonical fields
benchmark export session <session-uuid> --format csv

# Export session without request data
benchmark export session <session-uuid> --no-requests

# Export session without artifact registration
benchmark export session <session-uuid> --no-register

# Export session without secret redaction
benchmark export session <session-uuid> --no-redact
```

### Experiment Export

```bash
# Export experiment to JSON
benchmark export experiment <experiment-uuid>

# Export experiment with request-level data
benchmark export experiment <experiment-uuid> --requests

# Export experiment to CSV
benchmark export experiment <experiment-uuid> --format csv

# Export experiment to Parquet (requires pyarrow)
benchmark export experiment <experiment-uuid> --format parquet
```

## Canonical Fields Evidence

### Session Export Fields

The following fields are guaranteed to be present in all session exports:

```python
SESSION_EXPORT_FIELDS = [
    "id",
    "experiment_id",
    "variant_id",
    "task_card_id",
    "harness_profile",
    "repo_path",
    "git_branch",
    "git_commit",
    "git_dirty",
    "operator_label",
    "status",
    "outcome_state",
    "started_at",
    "ended_at",
    "duration_seconds",
    "created_at",
    "updated_at",
]
```

### Request Export Fields

The following fields are guaranteed to be present in all request exports:

```python
REQUEST_EXPORT_FIELDS = [
    "id",
    "request_id",
    "session_id",
    "provider",
    "model",
    "timestamp",
    "latency_ms",
    "ttft_ms",
    "tokens_prompt",
    "tokens_completion",
    "tokens_total",
    "error",
    "error_message",
    "cache_hit",
]
```

## Artifact Registration Evidence

The export commands automatically register artifacts with:

- **artifact_type**: "export"
- **content_type**: MIME type based on format
- **storage_path**: Absolute path to export file
- **size_bytes**: File size (auto-detected)
- **session_id** or **experiment_id**: Scope linkage
- **artifact_metadata**: Export options and timestamp

## Secret Redaction Evidence

By default, the following sensitive fields are excluded from exports:

```python
SENSITIVE_FIELDS = {
    "proxy_credential_id",
    "proxy_credential_alias",
    "api_key",
    "api_key_env",
    "upstream_base_url_env",
}
```

Users can override with `--no-redact` flag if needed.

## Acceptance Criteria Verification

- ✅ **Session and experiment exports contain stable canonical fields**
  - Defined in SESSION_EXPORT_FIELDS and REQUEST_EXPORT_FIELDS constants
  - CSV export uses canonical fieldnames with extrasaction="ignore"
  
- ✅ **Exported artifacts are registered in the benchmark database**
  - Artifact registration code in export.py lines 85-104 (session) and 183-203 (experiment)
  - Tests verify artifact creation
  
- ✅ **Exports exclude secrets and respect redaction defaults**
  - SENSITIVE_FIELDS constant defines redacted fields
  - redact_secrets parameter defaults to True
  - Tests verify redaction behavior

## PR and Commit Evidence

- **PR**: https://github.com/trilogy-group/StackPerf/pull/27
- **Branch**: COE-315-structured-export-commands
- **Commit**: a0502b9 (will be updated with CSV fix)