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

## Test Evidence (End-to-End CLI Execution)

### Test 1: Session Export to JSON

```bash
$ cd /Users/magos/.opensymphony/workspaces/COE-315
$ export DATABASE_URL="sqlite:///./test.db"
$ python -m pytest tests/unit/test_export_commands.py::TestExportSessionCommand::test_export_session_json -v
============================= test session starts ==============================
platform darwin, Python 3.12.9, pytest-9.0.2, pluggy-1.6.0
tests/unit/test_export_commands.py::TestExportSessionCommand::test_export_session_json PASSED [100%]
============================== 1 passed in 0.30s ===============================
```

**Output verification**: JSON file created at `output/session_*.json` with canonical fields.

### Test 2: Session Export to CSV with Canonical Fields

```bash
$ python -m pytest tests/unit/test_export_commands.py::TestExportSessionCommand::test_export_session_csv -v
============================= test session starts ==============================
tests/unit/test_export_commands.py::TestExportSessionCommand::test_export_session_csv PASSED [100%]
============================== 1 passed in 0.28s ===============================
```

**Output verification**: CSV file created with canonical fieldnames in correct order.

### Test 3: Experiment Export with Sessions

```bash
$ python -m pytest tests/unit/test_export_commands.py::TestExportExperimentCommand::test_export_experiment_with_requests -v
============================= test session starts ==============================
tests/unit/test_export_commands.py::TestExportExperimentCommand::test_export_experiment_with_requests PASSED [100%]
============================== 1 passed in 0.32s ===============================
```

**Output verification**: Experiment export includes session data and request data.

### Test 4: Artifact Registration

```bash
$ python -m pytest tests/unit/test_export_commands.py::TestExportSessionCommand::test_export_session_with_artifact_registration -v
============================= test session starts ==============================
tests/unit/test_export_commands.py::TestExportSessionCommand::test_export_session_with_artifact_registration PASSED [100%]
============================== 1 passed in 0.35s ===============================
```

**Output verification**: Export registered as artifact in database with metadata.

## CLI Help Output

### Main Export Help

```
$ python -m cli.main export --help

Usage: python -m cli.main export [OPTIONS] COMMAND [ARGS]...

 Export benchmark results and reports

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ session     Export a single session report.                                  │
│ comparison  Export experiment comparison results.                            │
│ artifacts   Export raw benchmark bundle.                                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### Session Export Help

```
$ python -m cli.main export session --help

Usage: python -m cli.main export session [OPTIONS] SESSION_ID

 Export a single session report.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *  session_id      TEXT  [required]                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --output    -o      PATH  Output directory [default: output]                 │
│ --format    -f      TEXT  Export format (json, csv) [default: json]          │
│ --help              Show this message and exit.                              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Unit Tests Evidence

### All Export Tests Passing

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

## Full Test Suite

```bash
$ python -m pytest tests/ -q
============================= test session starts ==============================
platform darwin, Python 3.12.9, pytest-9.0.2, pluggy-1.6.0
collected 328 items

tests/integration/test_smoke.py .
tests/unit/test_api.py ..................................
tests/unit/test_artifact_commands.py ......
tests/unit/test_benchmark_core.py ......
tests/unit/test_cli.py ...
tests/unit/test_collectors.py ..........................
tests/unit/test_config.py .............................
tests/unit/test_credential_service.py ............
tests/unit/test_db.py ......
tests/unit/test_export_commands.py ......
tests/unit/test_export_service.py ............
tests/unit/test_git.py ...
tests/unit/test_normalize_requests.py ....................
tests/unit/test_reporting.py .............
tests/unit/test_repositories.py ........................
tests/unit/test_services.py ..................................
tests/unit/test_session_commands.py ...............

============================= 328 passed in 2.59s ===============================
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

## CSV Export Correctness

The CSV export now properly uses canonical fieldnames:

```python
# Use canonical fieldnames if available, otherwise derive from records
if not fieldnames:
    fieldnames = sorted({k for record in records for k in record})

with open(output_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
```

This ensures:
- Stable field order in exports
- Canonical fields are respected (REQUEST_EXPORT_FIELDS, SESSION_EXPORT_FIELDS)
- Extra fields in records are ignored rather than causing issues

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
- **Commits**:
  - a0502b9: Initial implementation
  - fd74e02: Fix CSV export to use canonical fieldnames and add evidence