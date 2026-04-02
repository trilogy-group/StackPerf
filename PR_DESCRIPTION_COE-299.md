# COE-299: Security, Operations, and Delivery Quality

## Summary

This PR implements security controls, CI checks, and operational safeguards for the benchmark system as specified in COE-299.

## Changes

### 1. Secret Scanning CI Workflow (`.github/workflows/secret-scan.yml`)
- **detect-secrets job**: Uses Yelp's detect-secrets tool to scan for potential secrets
  - Excludes common non-source files (lock files, logs, markdown, tests)
  - Supports baseline comparison for gradual adoption
  - Fails on unaudited secrets in baseline
- **check-env-files job**: Prevents accidental commit of `.env` files
  - Finds all `.env*` files except `.env.example`
  - Fails if any environment files are detected
- **hardcoded-secrets check**: Pattern-based scanning for common secret formats
  - OpenAI API keys (`sk-*`)
  - Anthropic API keys (`sk-ant-*`)
  - AWS Access Key IDs (`AKIA*`)
  - 32-character hex secrets

### 2. Pre-commit Hooks (`.pre-commit-config.yaml`)
- **Standard hooks**: check-added-large-files, check-json, check-toml, check-yaml, debug-statements, detect-private-key, end-of-file-fixer, trailing-whitespace
- **detect-secrets integration**: Local secret scanning with baseline support
- **Ruff integration**: Linting and formatting checks on commit

### 3. CLI Operator Safeguards (`src/cli/commands/session.py`)
- **Configuration visibility**: `session create` now shows a summary table before creation
  - Experiment, Variant, Model, Provider, Task Card, Harness Profile
- **Duplicate session warning**: Detects existing active sessions for the same experiment+variant
  - Warns operator and requires explicit confirmation
  - `--force` flag available for automation
- **Next steps display**: After successful creation, shows commands to:
  - View session details
  - Get environment variables
  - List all sessions

### 4. Cleanup CLI Commands (`src/cli/commands/cleanup.py`)
- **`benchmark cleanup retention`**: Run retention cleanup with:
  - `--dry-run`: Preview what would be cleaned without making changes
  - `--force`: Skip confirmation prompt
  - `--type`: Target specific data type
  - `--batch-size`: Control processing batch size
- **`benchmark cleanup credentials`**: Clean up expired session credentials
  - Same `--dry-run` and `--force` options
- **`benchmark cleanup status`**: Display current retention policy status
  - Shows retention periods, cutoff dates, and archive settings for all data types

### 5. Security Implementation
- **RedactionFilter**: Already implemented in `benchmark_core/security.py`
  - Redacts API keys, database URLs, tokens from logs and exports
  - Pattern matching for common secret formats
- **ContentCaptureConfig**: Controls what content is captured
  - Prompts and responses disabled by default
  - Requires explicit opt-in with retention controls
- **RetentionSettings**: Configurable data lifecycle policies
  - Session credentials: 1 day retention
  - Raw ingestion: 7 days
  - Normalized requests: 30 days
  - Sessions: 90 days
  - Metric rollups: 90 days

## Acceptance Criteria

- [x] Secret scanning added to CI pipeline (detect-secrets workflow)
- [x] Pre-commit hooks configured for secret detection
- [x] CLI commands have confirmation for destructive operations
- [x] CLI provides clear visibility into selected config
- [x] Session creation warns about existing active sessions
- [x] All security tests pass (50/50)
- [x] All retention cleanup tests pass (24/24)
- [x] Quality checks pass (lint clean)

## Testing

```bash
# Run security tests
python -m pytest tests/unit/test_security.py -v
# 50 tests passed

# Run retention cleanup tests
python -m pytest tests/unit/test_retention_cleanup.py -v
# 24 tests passed

# Run quality checks
make lint
# All checks passed!
```

## Security Hardening

- No secrets committed to repository
- All session credentials use short TTL (1 day)
- Content capture disabled by default
- Secrets redacted from all logs and exports
- Cleanup commands require explicit confirmation

Closes COE-299
