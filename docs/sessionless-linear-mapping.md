# Sessionless Usage Linear Mapping

Generated from [docs/sessionless-plan.md](sessionless-plan.md) for the sessionless usage metrics implementation plan.

## Target

- Linear project: [StackPerf](https://linear.app/trilogy-ai-coe/project/stackperf-5250e49b61f4)
- Linear team: COE / Trilogy AI COE
- Project overview updated: yes

## Milestones

| Plan milestone | Linear milestone | Linear milestone ID |
| --- | --- | --- |
| M1 | M1: Sessionless Contracts | `3cb56a5b-1025-4c9a-ad62-2d192d6812cc` |
| M2 | M2: Key Registry | `121ddd1c-5f37-494a-8cfe-777a75a9d829` |
| M3 | M3: Usage Ingestion | `da92a34f-d88a-4e32-98c6-bb5cfb929428` |
| M4 | M4: Usage Metrics | `4b019513-c8c9-44b4-9c5f-8db806fc0b62` |
| M5 | M5: Release Readiness | `522a002a-6f10-4f45-bdb4-601d83a14e97` |

## Parent Issues

| Workstream | Linear issue | Milestone |
| --- | --- | --- |
| Sessionless Usage Architecture and Contracts | [COE-361](https://linear.app/trilogy-ai-coe/issue/COE-361/sessionless-usage-architecture-and-contracts) - Sessionless Usage Architecture and Contracts | M1: Sessionless Contracts |
| API Key Registry and Credential Operations | [COE-362](https://linear.app/trilogy-ai-coe/issue/COE-362/api-key-registry-and-credential-operations) - API Key Registry and Credential Operations | M2: Key Registry |
| Usage Ingestion and Normalization | [COE-363](https://linear.app/trilogy-ai-coe/issue/COE-363/usage-ingestion-and-normalization) - Usage Ingestion and Normalization | M3: Usage Ingestion |
| Usage Rollups, API, and Exports | [COE-364](https://linear.app/trilogy-ai-coe/issue/COE-364/usage-rollups-api-and-exports) - Usage Rollups, API, and Exports | M4: Usage Metrics |
| Usage Dashboards, Security, and Operations | [COE-365](https://linear.app/trilogy-ai-coe/issue/COE-365/usage-dashboards-security-and-operations) - Usage Dashboards, Security, and Operations | M5: Release Readiness |

## Sub-Issues

| Local task ID | Linear issue | Parent | Milestone |
| --- | --- | --- | --- |
| SESSIONLESS-001 | [COE-366](https://linear.app/trilogy-ai-coe/issue/COE-366/define-sessionless-usage-mode-contracts-and-adrs) - Define sessionless usage mode contracts and ADRs | COE-361 - Sessionless Usage Architecture and Contracts | M1: Sessionless Contracts |
| SESSIONLESS-002 | [COE-367](https://linear.app/trilogy-ai-coe/issue/COE-367/inventory-litellm-spend-log-fields-and-prometheus-labels-for-api-key) - Inventory LiteLLM spend log fields and Prometheus labels for API key attribution | COE-361 - Sessionless Usage Architecture and Contracts | M1: Sessionless Contracts |
| SESSIONLESS-003 | [COE-368](https://linear.app/trilogy-ai-coe/issue/COE-368/add-usage-mode-config-contracts-for-proxy-keys-and-default-usage) - Add usage-mode config contracts for proxy keys and default usage policies | COE-361 - Sessionless Usage Architecture and Contracts | M1: Sessionless Contracts |
| SESSIONLESS-004 | [COE-369](https://linear.app/trilogy-ai-coe/issue/COE-369/add-proxy-key-registry-schema-migrations-repositories-and-domain) - Add proxy key registry schema, migrations, repositories, and domain models | COE-362 - API Key Registry and Credential Operations | M2: Key Registry |
| SESSIONLESS-005 | [COE-370](https://linear.app/trilogy-ai-coe/issue/COE-370/implement-sessionless-litellm-key-creation-listing-revocation-and-info) - Implement sessionless LiteLLM key creation, listing, revocation, and info commands | COE-362 - API Key Registry and Credential Operations | M2: Key Registry |
| SESSIONLESS-006 | [COE-372](https://linear.app/trilogy-ai-coe/issue/COE-372/wire-benchmark-session-creation-to-real-litellm-credential-issuance) - Wire benchmark session creation to real LiteLLM credential issuance | COE-362 - API Key Registry and Credential Operations | M2: Key Registry |
| SESSIONLESS-007 | [COE-371](https://linear.app/trilogy-ai-coe/issue/COE-371/add-usage-request-schema-migration-repositories-and-indexes) - Add usage request schema, migration, repositories, and indexes | COE-363 - Usage Ingestion and Normalization | M3: Usage Ingestion |
| SESSIONLESS-008 | [COE-373](https://linear.app/trilogy-ai-coe/issue/COE-373/implement-sessionless-litellm-usage-collector-and-normalizer) - Implement sessionless LiteLLM usage collector and normalizer | COE-363 - Usage Ingestion and Normalization | M3: Usage Ingestion |
| SESSIONLESS-009 | [COE-374](https://linear.app/trilogy-ai-coe/issue/COE-374/add-usage-ingestion-watermarks-and-cli-collection-commands) - Add usage ingestion watermarks and CLI collection commands | COE-363 - Usage Ingestion and Normalization | M3: Usage Ingestion |
| SESSIONLESS-010 | [COE-375](https://linear.app/trilogy-ai-coe/issue/COE-375/reconcile-benchmark-request-ingestion-with-sessionless-usage-ingestion) - Reconcile benchmark request ingestion with sessionless usage ingestion | COE-363 - Usage Ingestion and Normalization | M3: Usage Ingestion |
| SESSIONLESS-011 | [COE-376](https://linear.app/trilogy-ai-coe/issue/COE-376/implement-usage-rollups-by-api-key-model-provider-and-time-bucket) - Implement usage rollups by API key, model, provider, and time bucket | COE-364 - Usage Rollups, API, and Exports | M4: Usage Metrics |
| SESSIONLESS-012 | [COE-377](https://linear.app/trilogy-ai-coe/issue/COE-377/add-usage-reporting-service-and-api-endpoints) - Add usage reporting service and API endpoints | COE-364 - Usage Rollups, API, and Exports | M4: Usage Metrics |
| SESSIONLESS-013 | [COE-378](https://linear.app/trilogy-ai-coe/issue/COE-378/add-usage-cli-summaries-and-exports) - Add usage CLI summaries and exports | COE-364 - Usage Rollups, API, and Exports | M4: Usage Metrics |
| SESSIONLESS-014 | [COE-379](https://linear.app/trilogy-ai-coe/issue/COE-379/add-grafana-dashboards-for-usage-by-api-key-and-model) - Add Grafana dashboards for usage by API key and model | COE-365 - Usage Dashboards, Security, and Operations | M5: Release Readiness |
| SESSIONLESS-015 | [COE-380](https://linear.app/trilogy-ai-coe/issue/COE-380/add-security-redaction-and-retention-controls-for-usage-mode) - Add security, redaction, and retention controls for usage mode | COE-365 - Usage Dashboards, Security, and Operations | M5: Release Readiness |
| SESSIONLESS-016 | [COE-381](https://linear.app/trilogy-ai-coe/issue/COE-381/document-and-verify-the-end-to-end-sessionless-usage-workflow) - Document and verify the end-to-end sessionless usage workflow | COE-365 - Usage Dashboards, Security, and Operations | M5: Release Readiness |

## Blocker Relationships

| Blocks | Blocked issue |
| --- | --- |
| [COE-366](https://linear.app/trilogy-ai-coe/issue/COE-366/define-sessionless-usage-mode-contracts-and-adrs) | [COE-367](https://linear.app/trilogy-ai-coe/issue/COE-367/inventory-litellm-spend-log-fields-and-prometheus-labels-for-api-key) |
| [COE-366](https://linear.app/trilogy-ai-coe/issue/COE-366/define-sessionless-usage-mode-contracts-and-adrs) | [COE-368](https://linear.app/trilogy-ai-coe/issue/COE-368/add-usage-mode-config-contracts-for-proxy-keys-and-default-usage) |
| [COE-366](https://linear.app/trilogy-ai-coe/issue/COE-366/define-sessionless-usage-mode-contracts-and-adrs) | [COE-369](https://linear.app/trilogy-ai-coe/issue/COE-369/add-proxy-key-registry-schema-migrations-repositories-and-domain) |
| [COE-367](https://linear.app/trilogy-ai-coe/issue/COE-367/inventory-litellm-spend-log-fields-and-prometheus-labels-for-api-key) | [COE-369](https://linear.app/trilogy-ai-coe/issue/COE-369/add-proxy-key-registry-schema-migrations-repositories-and-domain) |
| [COE-368](https://linear.app/trilogy-ai-coe/issue/COE-368/add-usage-mode-config-contracts-for-proxy-keys-and-default-usage) | [COE-370](https://linear.app/trilogy-ai-coe/issue/COE-370/implement-sessionless-litellm-key-creation-listing-revocation-and-info) |
| [COE-369](https://linear.app/trilogy-ai-coe/issue/COE-369/add-proxy-key-registry-schema-migrations-repositories-and-domain) | [COE-370](https://linear.app/trilogy-ai-coe/issue/COE-370/implement-sessionless-litellm-key-creation-listing-revocation-and-info) |
| [COE-369](https://linear.app/trilogy-ai-coe/issue/COE-369/add-proxy-key-registry-schema-migrations-repositories-and-domain) | [COE-372](https://linear.app/trilogy-ai-coe/issue/COE-372/wire-benchmark-session-creation-to-real-litellm-credential-issuance) |
| [COE-370](https://linear.app/trilogy-ai-coe/issue/COE-370/implement-sessionless-litellm-key-creation-listing-revocation-and-info) | [COE-372](https://linear.app/trilogy-ai-coe/issue/COE-372/wire-benchmark-session-creation-to-real-litellm-credential-issuance) |
| [COE-367](https://linear.app/trilogy-ai-coe/issue/COE-367/inventory-litellm-spend-log-fields-and-prometheus-labels-for-api-key) | [COE-371](https://linear.app/trilogy-ai-coe/issue/COE-371/add-usage-request-schema-migration-repositories-and-indexes) |
| [COE-369](https://linear.app/trilogy-ai-coe/issue/COE-369/add-proxy-key-registry-schema-migrations-repositories-and-domain) | [COE-371](https://linear.app/trilogy-ai-coe/issue/COE-371/add-usage-request-schema-migration-repositories-and-indexes) |
| [COE-367](https://linear.app/trilogy-ai-coe/issue/COE-367/inventory-litellm-spend-log-fields-and-prometheus-labels-for-api-key) | [COE-373](https://linear.app/trilogy-ai-coe/issue/COE-373/implement-sessionless-litellm-usage-collector-and-normalizer) |
| [COE-371](https://linear.app/trilogy-ai-coe/issue/COE-371/add-usage-request-schema-migration-repositories-and-indexes) | [COE-373](https://linear.app/trilogy-ai-coe/issue/COE-373/implement-sessionless-litellm-usage-collector-and-normalizer) |
| [COE-373](https://linear.app/trilogy-ai-coe/issue/COE-373/implement-sessionless-litellm-usage-collector-and-normalizer) | [COE-374](https://linear.app/trilogy-ai-coe/issue/COE-374/add-usage-ingestion-watermarks-and-cli-collection-commands) |
| [COE-373](https://linear.app/trilogy-ai-coe/issue/COE-373/implement-sessionless-litellm-usage-collector-and-normalizer) | [COE-375](https://linear.app/trilogy-ai-coe/issue/COE-375/reconcile-benchmark-request-ingestion-with-sessionless-usage-ingestion) |
| [COE-374](https://linear.app/trilogy-ai-coe/issue/COE-374/add-usage-ingestion-watermarks-and-cli-collection-commands) | [COE-375](https://linear.app/trilogy-ai-coe/issue/COE-375/reconcile-benchmark-request-ingestion-with-sessionless-usage-ingestion) |
| [COE-371](https://linear.app/trilogy-ai-coe/issue/COE-371/add-usage-request-schema-migration-repositories-and-indexes) | [COE-376](https://linear.app/trilogy-ai-coe/issue/COE-376/implement-usage-rollups-by-api-key-model-provider-and-time-bucket) |
| [COE-374](https://linear.app/trilogy-ai-coe/issue/COE-374/add-usage-ingestion-watermarks-and-cli-collection-commands) | [COE-376](https://linear.app/trilogy-ai-coe/issue/COE-376/implement-usage-rollups-by-api-key-model-provider-and-time-bucket) |
| [COE-376](https://linear.app/trilogy-ai-coe/issue/COE-376/implement-usage-rollups-by-api-key-model-provider-and-time-bucket) | [COE-377](https://linear.app/trilogy-ai-coe/issue/COE-377/add-usage-reporting-service-and-api-endpoints) |
| [COE-376](https://linear.app/trilogy-ai-coe/issue/COE-376/implement-usage-rollups-by-api-key-model-provider-and-time-bucket) | [COE-378](https://linear.app/trilogy-ai-coe/issue/COE-378/add-usage-cli-summaries-and-exports) |
| [COE-376](https://linear.app/trilogy-ai-coe/issue/COE-376/implement-usage-rollups-by-api-key-model-provider-and-time-bucket) | [COE-379](https://linear.app/trilogy-ai-coe/issue/COE-379/add-grafana-dashboards-for-usage-by-api-key-and-model) |
| [COE-377](https://linear.app/trilogy-ai-coe/issue/COE-377/add-usage-reporting-service-and-api-endpoints) | [COE-379](https://linear.app/trilogy-ai-coe/issue/COE-379/add-grafana-dashboards-for-usage-by-api-key-and-model) |
| [COE-369](https://linear.app/trilogy-ai-coe/issue/COE-369/add-proxy-key-registry-schema-migrations-repositories-and-domain) | [COE-380](https://linear.app/trilogy-ai-coe/issue/COE-380/add-security-redaction-and-retention-controls-for-usage-mode) |
| [COE-371](https://linear.app/trilogy-ai-coe/issue/COE-371/add-usage-request-schema-migration-repositories-and-indexes) | [COE-380](https://linear.app/trilogy-ai-coe/issue/COE-380/add-security-redaction-and-retention-controls-for-usage-mode) |
| [COE-378](https://linear.app/trilogy-ai-coe/issue/COE-378/add-usage-cli-summaries-and-exports) | [COE-380](https://linear.app/trilogy-ai-coe/issue/COE-380/add-security-redaction-and-retention-controls-for-usage-mode) |
| [COE-370](https://linear.app/trilogy-ai-coe/issue/COE-370/implement-sessionless-litellm-key-creation-listing-revocation-and-info) | [COE-381](https://linear.app/trilogy-ai-coe/issue/COE-381/document-and-verify-the-end-to-end-sessionless-usage-workflow) |
| [COE-374](https://linear.app/trilogy-ai-coe/issue/COE-374/add-usage-ingestion-watermarks-and-cli-collection-commands) | [COE-381](https://linear.app/trilogy-ai-coe/issue/COE-381/document-and-verify-the-end-to-end-sessionless-usage-workflow) |
| [COE-377](https://linear.app/trilogy-ai-coe/issue/COE-377/add-usage-reporting-service-and-api-endpoints) | [COE-381](https://linear.app/trilogy-ai-coe/issue/COE-381/document-and-verify-the-end-to-end-sessionless-usage-workflow) |
| [COE-378](https://linear.app/trilogy-ai-coe/issue/COE-378/add-usage-cli-summaries-and-exports) | [COE-381](https://linear.app/trilogy-ai-coe/issue/COE-381/document-and-verify-the-end-to-end-sessionless-usage-workflow) |
| [COE-379](https://linear.app/trilogy-ai-coe/issue/COE-379/add-grafana-dashboards-for-usage-by-api-key-and-model) | [COE-381](https://linear.app/trilogy-ai-coe/issue/COE-381/document-and-verify-the-end-to-end-sessionless-usage-workflow) |
| [COE-380](https://linear.app/trilogy-ai-coe/issue/COE-380/add-security-redaction-and-retention-controls-for-usage-mode) | [COE-381](https://linear.app/trilogy-ai-coe/issue/COE-381/document-and-verify-the-end-to-end-sessionless-usage-workflow) |

## Validation

- [x] All expected blocker relationships exist in Linear.
- [x] No stale `SESSIONLESS-*` identifiers remain in Linear issue descriptions.
- [x] All sub-issues are linked to the expected parent issues.
- [x] All issues are assigned to the expected project milestones.
- [x] The Linear project overview includes the sessionless usage metrics plan section.

Validation details:

- Missing relations: 0
- Stale local IDs in descriptions: 0
- Wrong parent links: 0
- Wrong milestones: 0
