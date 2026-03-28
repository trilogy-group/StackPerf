# Security and Operations

## Local-first operating posture

The system is designed for local use on a developer workstation or controlled internal environment.

Default posture:

- services bind to local interfaces unless explicitly configured otherwise
- dashboards are local-only by default
- benchmark content capture is off by default
- secrets are injected through environment variables or uncommitted env files

## Secrets

Secrets include:

- upstream provider API keys
- LiteLLM master key
- session-scoped proxy credentials
- Grafana admin credentials
- database connection strings

Rules:

- never commit secrets
- never place secrets in sample config values unless clearly fake
- never log session credentials in plaintext after creation output
- use short TTLs for session-scoped proxy credentials

## Redaction

Default benchmark storage should capture metadata and metrics, not content.

Allowed by default:

- request IDs
- timing metrics
- token counts
- cache counters
- routing metadata
- status and error class

Disabled by default:

- prompt text
- response text
- tool payload bodies

### Redaction Implementation

The system enforces secret redaction through:

1. **RedactionFilter**: Automatically redacts secrets from logs, exports, and string representations
2. **Pattern Detection**: Recognizes common secret patterns (API keys, tokens, database URLs)
3. **Safe Logging**: All log outputs pass through redaction filter

Supported secret patterns:

- OpenAI-style API keys (`sk-*`)
- Anthropic-style API keys (`sk-ant-*`)
- Generic API keys and bearer tokens
- Database connection strings (PostgreSQL, MySQL, Redis, MongoDB)
- AWS credentials
- Environment variables with secret-like names (PASSWORD, SECRET, KEY, TOKEN, CREDENTIAL)

### Content Capture Configuration

Content capture is controlled by `ContentCaptureConfig`:

```python
from benchmark_core.security import ContentCaptureConfig

# Default: all content capture disabled
config = ContentCaptureConfig()

# Enable prompt capture (requires explicit opt-in)
config = ContentCaptureConfig(
    enabled=True,
    capture_prompts=True,
    capture_responses=False,  # Still disabled
)

# Maximum content length
config.max_content_length = 10000  # characters

# Redact secrets within captured content
config.redact_secrets_in_content = True  # Always True by default
```

### Secret Leak Prevention

The system prevents secret leaks in:

- **Logs**: All logged strings and data structures are filtered
- **Exports**: Export artifacts pass through redaction layer
- **Error messages**: Stack traces and error details are sanitized
- **Database queries**: Query logs never include secret values

## Retention

Retention policy applies to:

- raw LiteLLM ingestion records
- normalized request rows
- exported artifacts
- session credentials

### Retention Settings

Default retention periods:

| Data Type | Retention Days | Notes |
|-----------|---------------|-------|
| Raw ingestion records | 7 | Short-lived raw data |
| Normalized requests | 30 | Longer-lived processed data |
| Sessions | 90 | Benchmark session records |
| Session credentials | 1 | Very short TTL for security |
| Artifacts | 30 | Export files (archived before deletion) |
| Metric rollups | 90 | Aggregated metrics |

### Retention Configuration

Retention is configured through `RetentionSettings`:

```python
from benchmark_core.security import RetentionSettings, RetentionPolicy

# Use defaults
settings = RetentionSettings()

# Customize a specific policy
settings.session_credentials = RetentionPolicy(
    data_type="session_credentials",
    retention_days=1,
    min_age_days=0,  # Can cleanup immediately after expiration
)

# Disable retention for a data type (keep forever)
settings.sessions = RetentionPolicy(
    data_type="sessions",
    retention_days=None,  # No cleanup
)
```

### Cleanup Jobs

Retention is enforced through cleanup jobs:

```python
from collectors.retention_cleanup import RetentionCleanupJob

# Run cleanup for all data types
job = RetentionCleanupJob()
diagnostics = await job.run_cleanup()

# Run cleanup for specific types
diagnostics = await job.run_cleanup(
    data_types=["session_credentials", "raw_ingestion"]
)

# Check cleanup results
for data_type, result in diagnostics.cleanup_stats.items():
    print(f"{data_type}: deleted {result.deleted_count} records")
```

### Cleanup Safety Features

- **Minimum age**: Records younger than `min_age_days` are never deleted
- **Batch processing**: Cleanup processes records in configurable batches
- **Archive before delete**: Artifacts can be archived before deletion
- **Audit trail**: All cleanup operations are logged with statistics

### Session Credential Lifecycle

Session credentials have special handling:

1. **Creation**: Credential issued with short TTL (typically 1 day)
2. **Active**: Credential used for session duration
3. **Expiration**: Credential automatically expires after TTL
4. **Revocation**: Credential can be manually revoked via cleanup job
5. **Cleanup**: Expired/revoked credentials are cleaned up daily

```python
from collectors.retention_cleanup import CredentialCleanupJob

# Cleanup expired credentials
job = CredentialCleanupJob()
result = await job.cleanup_expired_credentials()

print(f"Checked: {result.total_checked}")
print(f"Revoked: {result.revoked_count}")
print(f"Expired: {result.expired_count}")
```

## Operator safeguards

The CLI should provide:

- explicit confirmation when deleting benchmark data
- clear status output when a session has not been finalized
- validation before creating a session that would overwrite local artifacts
- visibility into the exact base URL, model alias, and harness profile selected

## Upgrade and pinning policy

Pin versions for:

- LiteLLM
- benchmark application dependencies
- Prometheus
- Grafana

Each benchmark result should record the versions in use so regressions can be linked to stack changes.

## Service health

Operators need quick checks for:

- LiteLLM health endpoint
- Postgres availability
- Prometheus scrape success
- Grafana datasource health
- benchmark database migration state

## Failure handling

The system must fail clearly when:

- the proxy is unreachable
- the benchmark database is unavailable
- the chosen provider route is not configured
- the requested harness profile is invalid
- the session credential cannot be created

Silent fallback to a different provider, model, or endpoint is not acceptable.

## Local filesystem hygiene

The benchmark application may inspect the local repository and write exports.

Rules:

- store generated env snippets and exports in ignored paths
- do not write secrets into tracked files
- include a clear cleanup command for generated session artifacts

## Auditability

A benchmark result must be auditable after the session ends.

Store enough metadata to answer:

- which config files defined the session
- which repository commit was used
- which provider route and model were selected
- which harness profile was rendered
- when the session ran
- which requests were observed
