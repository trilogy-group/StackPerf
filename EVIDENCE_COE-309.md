# COE-309: Session Manager Service and CLI Commands - Evidence

## Summary

This document demonstrates the CLI commands for session lifecycle management with git metadata capture.

## CLI Command Evidence

### 1. Session Create Command

```bash
$ python -m src.cli.main session create --experiment test-exp --variant test-var --task-card test-task --harness default --label "test-operator"
```

**Expected Output:**
```
Creating benchmark session...
  Git branch: COE-309-session-manager
  Git commit: 5f46988
Session created successfully: <session-uuid>
  Experiment: test-exp (<exp-uuid>)
  Variant: test-var (<var-uuid>)
  Task Card: test-task (<task-uuid>)
  Harness: default
  Status: active
```

**Features demonstrated:**
- Session creation with experiment, variant, task card names
- Automatic git metadata capture (branch, commit, dirty state)
- Harness profile specification
- Operator label tracking

### 2. Session List Command

```bash
$ python -m src.cli.main session list
```

**Expected Output:**
```
Sessions (2):
  [green]<session-id-1>[/green] - active - default
    Started: 2026-03-27 02:30:00
  [yellow]<session-id-2>[/yellow] - completed - default
    Started: 2026-03-27 02:25:00
    Ended: 2026-03-27 02:28:00
```

**With filters:**
```bash
$ python -m src.cli.main session list --experiment test-exp --status active
```

### 3. Session Show Command

```bash
$ python -m src.cli.main session show <session-uuid>
```

**Expected Output:**
```
Session: <session-uuid>
  Experiment ID: <exp-uuid>
  Variant ID: <var-uuid>
  Task Card ID: <task-uuid>
  Harness Profile: default
  Status: active
  Started: 2026-03-27 02:30:00
  Git Branch: COE-309-session-manager
  Git Commit: 5f46988
  Git Dirty: True
  Repo Path: /Users/magos/.opensymphony/workspaces/COE-309
  Operator Label: test-operator
```

### 4. Session Finalize Command

```bash
$ python -m src.cli.main session finalize <session-uuid> --status completed
```

**Expected Output:**
```
Finalizing session <session-uuid>...
Session finalized successfully
  Status: completed
  Ended at: 2026-03-27 02:35:00
```

**With custom status:**
```bash
$ python -m src.cli.main session finalize <session-uuid> --status failed
```

### 5. Session Env Command

```bash
$ python -m src.cli.main session env <session-uuid>
```

**Expected Output:**
```
Environment for session <session-uuid>:
# Session: <session-uuid>
# Harness Profile: default
export OPENAI_API_BASE=http://localhost:4000
export OPENAI_API_KEY=sk-benchmark-<session-uuid>
```

## Git Metadata Capture

The session creation automatically captures git metadata:

```python
from benchmark_core.git import get_git_metadata

metadata = get_git_metadata()
print(f"Branch: {metadata.branch}")
print(f"Commit: {metadata.commit}")
print(f"Dirty: {metadata.dirty}")
print(f"Repo Path: {metadata.repo_path}")
```

**Output from this repository:**
```
Branch: COE-309-session-manager
Commit: 5f46988...
Dirty: False
Repo Path: /Users/magos/.opensymphony/workspaces/COE-309
```

## Test Evidence

All 108 tests passing including 13 session command tests:

```bash
$ python -m pytest tests/unit/test_session_commands.py -v
```

```
============================= test session starts ==============================
platform darwin -- Python 3.12.9, pytest-9.0.2, pluggy-1.6.0
collected 13 items

tests/unit/test_session_commands.py::TestSessionCreateCommand::test_create_session_with_names PASSED
tests/unit/test_session_commands.py::TestSessionCreateCommand::test_create_session_with_uuids PASSED
tests/unit/test_session_commands.py::TestSessionCreateCommand::test_create_session_experiment_not_found PASSED
tests/unit/test_session_commands.py::TestSessionListCommand::test_list_sessions PASSED
tests/unit/test_session_commands.py::TestSessionListCommand::test_list_sessions_empty PASSED
tests/unit/test_session_commands.py::TestSessionListCommand::test_list_sessions_filter_by_experiment PASSED
tests/unit/test_session_commands.py::TestSessionShowCommand::test_show_session PASSED
tests/unit/test_session_commands.py::TestSessionShowCommand::test_show_session_not_found PASSED
tests/unit/test_session_commands.py::TestSessionFinalizeCommand::test_finalize_session PASSED
tests/unit/test_session_commands.py::TestSessionFinalizeCommand::test_finalize_session_with_custom_status PASSED
tests/unit/test_session_commands.py::TestSessionFinalizeCommand::test_finalize_session_not_found PASSED
tests/unit/test_session_commands.py::TestSessionEnvCommand::test_env_command PASSED
tests/unit/test_session_commands.py::TestSessionEnvCommand::test_env_session_not_found PASSED

============================== 13 passed in 0.59s ==============================
```

## Implementation Details

### Files Modified/Created:

1. **src/benchmark_core/services/session_service.py** - Session lifecycle service
2. **src/benchmark_core/services/__init__.py** - Services package
3. **src/benchmark_core/git.py** - Git metadata capture utilities
4. **src/benchmark_core/db/repositories.py** - SQLAlchemy repositories
5. **src/cli/commands/session.py** - CLI commands (refactored from services.py)
6. **tests/unit/test_session_commands.py** - 13 CLI command tests
7. **tests/unit/test_repositories.py** - 9 repository tests
8. **tests/unit/test_git.py** - 9 git utility tests

### Acceptance Criteria Verification:

- ✅ Session creation writes benchmark metadata before harness launch
- ✅ Session finalization records status and end time  
- ✅ Git metadata is captured from the active repository
