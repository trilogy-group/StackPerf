# ADR-002: API Key Attribution and Redaction

## Status

Accepted

## Context

StackPerf routes all traffic through a local LiteLLM proxy. LiteLLM supports virtual keys with aliases, budgets, and metadata. In benchmark mode, the system creates one session-scoped virtual key per session. In usage mode, operators may create long-lived proxy keys that are not tied to any benchmark session.

To attribute usage to owners, teams, and customers, the system needs a non-secret registry of proxy key metadata. At the same time, raw API key secrets must never be stored in the benchmark database, logs, exports, or dashboards.

## Canonical Terms

See `docs/config-and-contracts.md` for the canonical glossary. This ADR uses the same terms without duplication.

> **Proxy key ID vs Proxy key**: The `Proxy key ID` is the LiteLLM-internal identifier (a UUID or opaque string assigned by LiteLLM when the key is created). The `Proxy key` is the actual secret string (e.g., `sk-...`) that the client sends in the `Authorization` header. These are different values: the ID is used for lookup and logging, while the secret is used for authentication. Only the Proxy key ID (not the secret) may appear in LiteLLM logs, and even the ID must be redacted before persistence in the benchmark database.

## Attribution Contract

### What the benchmark system stores

The benchmark database stores only **non-secret** key metadata:

- `key_alias` — the human-readable alias (unique within the system)
- `owner` — free-text owner label
- `team` — team identifier
- `customer` — customer or cost-center label
- `description` — optional human-readable note
- `created_at`, `revoked_at`, `expires_at` — lifecycle timestamps
- `budget_duration`, `budget_amount` — budget configuration (not spend data)
- `metadata` — key-value tags (e.g., `{"environment": "staging"}`)

### What the benchmark system never stores

- The raw LiteLLM virtual key secret (the `sk-...` string).
- Any upstream provider API key secrets.
- Bearer tokens, database URLs, or other credential material in `metadata`.

### What LiteLLM logs contain

LiteLLM spend logs and request logs contain the virtual key ID. The benchmark collectors read these logs, match the key ID to the local registry entry by alias, and then drop the raw key ID before persistence. If a log references a key that has no registry entry, the collector stores `key_alias = null` and logs a warning.

### Redaction rules

1. **Ingestion redaction**: Before writing a `usage_requests` row, the collector must replace any raw virtual key ID with the corresponding `key_alias` from the registry. If no alias is found, the field is left null.
2. **Export redaction**: Any export or API response that includes usage rows must include only `key_alias`, never the raw key ID.
3. **Log redaction**: Application logs that mention keys must log the alias, never the secret.
4. **Audit trail**: The collector should record how many rows were ingested with missing aliases so operators can detect unattributed traffic.

## Storage Strategy

### Registry table: `proxy_keys`

| Field | Type | Notes |
|-------|------|-------|
| `proxy_key_id` | UUID or auto-increment, PK | Stable surrogate key; survives alias renames and reissues |
| `key_alias` | string, unique | Human-readable, non-secret identifier (e.g., `team-alpha-gpt4o`) |
| `owner` | string, nullable | Attribution owner |
| `team` | string, nullable | Team grouping |
| `customer` | string, nullable | Customer or cost-center |
| `description` | string, nullable | Human note |
| `budget_duration` | string, nullable | e.g., `1d`, `7d` |
| `budget_amount` | numeric, nullable | Budget limit |
| `created_at` | timestamp | Key creation time |
| `revoked_at` | timestamp, nullable | When revoked |
| `expires_at` | timestamp, nullable | When it expires |
| `metadata` | jsonb, nullable | Key-value tags |

### Usage table: `usage_requests`

Attribution fields:

| Field | Type | Notes |
|-------|------|-------|
| `proxy_key_id` | FK -> `proxy_keys.proxy_key_id` | Null if key not in registry; collector resolves via ephemeral mapping |
| `key_alias` | string, nullable | Denormalized from registry at ingestion time; retains alias at time of request |
| `owner` | string, nullable | Denormalized from registry at ingestion time |
| `team` | string, nullable | Denormalized from registry at ingestion time |
| `customer` | string, nullable | Denormalized from registry at ingestion time |

Denormalized fields are populated at ingestion so that rollups and queries do not need to join `proxy_keys` for every aggregation. If a key is later updated (e.g., team change), historical usage rows retain the values that were current at ingestion time. This is intentional: usage records are immutable facts.

## Consequences

- Raw key secrets are never in the benchmark database.
- Attribution queries are fast because `owner`, `team`, and `customer` are stored on `usage_requests`.
- Operators can update key metadata without rewriting historical usage rows.
- Missing registry entries are visible through null `proxy_key_id` counts and collector warnings.
- The system can support multiple keys per owner/team/customer without losing granularity.
- Alias renames and reissues are supported because `key_alias` is not the primary key.

## Related

- `docs/security-and-operations.md` — redaction and retention controls
- `docs/data-model-and-observability.md` — `proxy_keys` and `usage_requests` schema
- `docs/config-and-contracts.md` — canonical terms
