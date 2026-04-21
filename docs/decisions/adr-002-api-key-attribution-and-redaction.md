# ADR-002: API Key Attribution and Redaction

## Status

Accepted

## Context

StackPerf routes all traffic through a local LiteLLM proxy. LiteLLM supports virtual keys with aliases, budgets, and metadata. In benchmark mode, the system creates one session-scoped virtual key per session. In usage mode, operators may create long-lived proxy keys that are not tied to any benchmark session.

To attribute usage to owners, teams, and customers, the system needs a non-secret registry of proxy key metadata. At the same time, raw API key secrets must never be stored in the benchmark database, logs, exports, or dashboards.

## Canonical Terms

See `docs/config-and-contracts.md` for the canonical glossary. The following terms are expanded here only when this ADR adds key-management-specific nuance:

- **Proxy key ID** (`proxy_key_id`) — The stable surrogate identifier in the benchmark registry (auto-increment or UUID). This is non-secret and is the canonical foreign key for `usage_requests`.
- **LiteLLM virtual key ID** — The LiteLLM-internal identifier (e.g., `sk-...`). This is a secret and must not be persisted in the benchmark database.
- All other terms (`Proxy key`, `Key alias`, `Usage request`, `Usage rollup`, `Owner`, `Team`, `Customer`, `Time bucket`) are defined in `docs/config-and-contracts.md`.

## Attribution Contract

### What the benchmark system stores

The benchmark database stores only **non-secret** key metadata:

- `proxy_key_id` — stable surrogate primary key (auto-increment or UUID), non-secret
- `key_alias` — the human-readable alias (unique within the system, non-secret)
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

LiteLLM spend logs and request logs contain the LiteLLM virtual key ID (`sk-...`). This is a secret and must never be persisted in the benchmark database. The collector resolves this secret ID to a stable, non-secret registry identifier through one of the following mechanisms, configured at deployment time:

- **Ephemeral collector mapping** (default): The collector builds an in-memory map from LiteLLM virtual key ID (`sk-...`) to `proxy_key_id` at startup. Because the `proxy_keys` registry does not store the raw `sk-...` value, the collector must first obtain the `sk-...` -> `key_alias` mapping from an external source (e.g., a live LiteLLM admin API query or a sidecar file), then join to `proxy_keys` by `key_alias` to resolve the stable `proxy_key_id`. The resulting map is held only in memory and rebuilt at each startup. The raw `sk-...` value is used only during this resolution, never written.
- **Sidecar file** (alternative for air-gapped or high-security environments): A process outside the benchmark database periodically syncs the mapping to a local file. The collector reads the sidecar file at startup and uses it for resolution. The sidecar is stored outside the benchmark database backup scope.
- **Live LiteLLM admin API lookup** (alternative for dynamic environments): The collector queries the LiteLLM admin API at ingestion time to resolve a virtual key ID to its alias or `proxy_key_id`. The raw key ID is discarded after resolution.

In all mechanisms, the raw LiteLLM virtual key ID is dropped before any benchmark database write. If a log references a key that has no registry entry, the collector stores `proxy_key_id = null` and `key_alias = null`, and logs a warning.

### Redaction rules

1. **Ingestion redaction**: Before writing a `usage_requests` row, the collector must resolve the raw LiteLLM virtual key ID to the stable `proxy_key_id` (and denormalized `key_alias`) from the registry through the configured collector mapping mechanism. The raw `sk-...` value is never stored. If no registry entry is found, `proxy_key_id` and `key_alias` are left null.
2. **Export redaction**: Any export or API response that includes usage rows must include only `proxy_key_id` and `key_alias`, never the raw LiteLLM virtual key ID.
3. **Log redaction**: Application logs that mention keys must log `proxy_key_id` or `key_alias`, never the secret.
4. **Audit trail**: The collector should record how many rows were ingested with missing registry entries so operators can detect unattributed traffic.

## Storage Strategy

### Registry table: `proxy_keys`

| Field | Type | Notes |
|-------|------|-------|
| `proxy_key_id` | UUID or auto-increment, PK | Stable surrogate identifier, non-secret |
| `key_alias` | string, unique | Human-readable, unique, non-secret |
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
| `proxy_key_id` | UUID or int, FK → `proxy_keys.proxy_key_id` | Null if key not in registry |
| `key_alias` | string, nullable | Denormalized from registry at ingestion time |
| `owner` | string, nullable | Denormalized from registry at ingestion time |
| `team` | string, nullable | Denormalized from registry at ingestion time |
| `customer` | string, nullable | Denormalized from registry at ingestion time |
| `cost` | numeric, nullable | Total spend from LiteLLM spend logs when available |

Denormalized fields are populated at ingestion so that rollups and queries do not need to join `proxy_keys` for every aggregation. If a key is later updated (e.g., team change), historical usage rows retain the values that were current at ingestion time. This is intentional: usage records are immutable facts.

## Consequences

- Raw key secrets are never in the benchmark database.
- Attribution queries are fast because `owner`, `team`, and `customer` are stored on `usage_requests`.
- Operators can update key metadata without rewriting historical usage rows.
- Missing registry entries are visible through null `proxy_key_id` counts and collector warnings.
- The system can support multiple keys per owner/team/customer without losing granularity.

## Related

- `docs/security-and-operations.md` — redaction and retention controls
- `docs/data-model-and-observability.md` — `proxy_keys` and `usage_requests` schema
- `docs/config-and-contracts.md` — canonical terms
