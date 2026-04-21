# ADR-002: API Key Attribution and Redaction

## Status

Accepted

## Context

StackPerf routes all traffic through a local LiteLLM proxy. LiteLLM supports virtual keys with aliases, budgets, and metadata. In benchmark mode, the system creates one session-scoped virtual key per session. In usage mode, operators may create long-lived proxy keys that are not tied to any benchmark session.

To attribute usage to owners, teams, and customers, the system needs a non-secret registry of proxy key metadata. At the same time, raw API key secrets must never be stored in the benchmark database, logs, exports, or dashboards.

## Canonical Terms

| Term | Definition |
|------|------------|
| **Proxy key** | A LiteLLM virtual key (the actual secret string) issued by the LiteLLM proxy. |
| **Key alias** | A human-readable identifier assigned to a proxy key at creation time (e.g., `team-alpha-gpt4o`). Aliases are non-secret and stored in the benchmark registry. |
| **Proxy key ID** | The LiteLLM-internal identifier for a virtual key (e.g., `sk-...`). This is a secret and must not be persisted. |
| **Usage request** | One normalized LLM call observed through LiteLLM, stored in `usage_requests`. |
| **Usage rollup** | A derived summary of usage requests grouped by one or more dimensions (e.g., key alias, model, time bucket). |
| **Owner** | The entity responsible for a proxy key (e.g., a person, service account, or team). |
| **Team** | An organizational grouping that owns one or more proxy keys. |
| **Customer** | An external billing or cost-center label attached to a proxy key for charge-back. |
| **Time bucket** | A fixed time interval (e.g., hour, day) used to aggregate usage rollups. |

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
| `key_alias` | string, PK | Human-readable, unique, non-secret |
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
| `key_alias` | string, FK → `proxy_keys.key_alias` | Null if key not in registry |
| `owner` | string, nullable | Denormalized from registry at ingestion time |
| `team` | string, nullable | Denormalized from registry at ingestion time |
| `customer` | string, nullable | Denormalized from registry at ingestion time |

Denormalized fields are populated at ingestion so that rollups and queries do not need to join `proxy_keys` for every aggregation. If a key is later updated (e.g., team change), historical usage rows retain the values that were current at ingestion time. This is intentional: usage records are immutable facts.

## Consequences

- Raw key secrets are never in the benchmark database.
- Attribution queries are fast because `owner`, `team`, and `customer` are stored on `usage_requests`.
- Operators can update key metadata without rewriting historical usage rows.
- Missing registry entries are visible through null `key_alias` counts and collector warnings.
- The system can support multiple keys per owner/team/customer without losing granularity.

## Related

- `docs/security-and-operations.md` — redaction and retention controls
- `docs/data-model-and-observability.md` — `proxy_keys` and `usage_requests` schema
- `docs/config-and-contracts.md` — canonical terms
