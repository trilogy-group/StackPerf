# Evidence: COE-314 - Comparison Service and Experiment Summary Views

## Implementation Summary

This document provides evidence that the comparison service and summary views are implemented correctly.

## ComparisonService Methods

### compare_variants()

Compares all variants within an experiment across key latency and error metrics.

```python
from reporting.comparison import ComparisonService
from sqlalchemy.orm import Session

# Example usage:
service = ComparisonService(db_session)
variants = await service.compare_variants(
    experiment_id=uuid.UUID("..."),
    include_invalid=False,  # Excludes invalid sessions by default
    order_by="variant_name"
)

# Returns list of VariantComparison objects with:
# - variant_id, variant_name, provider, model, harness_profile
# - session_count, total_requests
# - avg_latency_ms, avg_ttft_ms
# - total_errors, error_rate
```

**SQL Query Generated** (from queries.py):
```sql
SELECT
    v.id as variant_id,
    v.name as variant_name,
    v.provider,
    v.model_alias,
    v.harness_profile,
    COUNT(DISTINCT s.id) as session_count,
    COUNT(r.id) as total_requests,
    AVG(r.latency_ms) as avg_latency_ms,
    AVG(r.ttft_ms) as avg_ttft_ms,
    SUM(CASE WHEN r.error THEN 1 ELSE 0 END) as total_errors,
    SUM(CASE WHEN r.cache_hit THEN 1 ELSE 0 END) as cache_hits
FROM variants v
LEFT JOIN sessions s ON s.variant_id = v.id
    AND (s.outcome_state IS NULL OR s.outcome_state != 'invalid')
LEFT JOIN requests r ON r.session_id = s.id
WHERE v.id IN (
    SELECT ev.variant_id FROM experiment_variants ev
    WHERE ev.experiment_id = :experiment_id
)
GROUP BY v.id, v.name, v.provider, v.model_alias, v.harness_profile
ORDER BY v.name ASC
```

### compare_providers()

Aggregates metrics by provider across all variants in an experiment.

```python
providers = await service.compare_providers(
    experiment_id=uuid.UUID("..."),
    include_invalid=False
)

# Returns list of ProviderComparison:
# - provider, session_count, total_requests
# - avg_latency_ms, avg_ttft_ms
# - total_errors, error_rate, variant_count
```

### compare_models()

Aggregates metrics by provider + model combination.

```python
models = await service.compare_models(
    experiment_id=uuid.UUID("..."),
    include_invalid=False
)

# Returns list of ModelComparison:
# - provider, model, session_count, total_requests
# - avg_latency_ms, avg_ttft_ms
# - total_errors, error_rate
```

### compare_harness_profiles()

Aggregates metrics by harness profile.

```python
profiles = await service.compare_harness_profiles(
    experiment_id=uuid.UUID("..."),
    include_invalid=False
)

# Returns list of HarnessProfileComparison:
# - harness_profile, session_count, total_requests
# - avg_latency_ms, avg_ttft_ms
# - total_errors, error_rate, variant_count
```

### compare_sessions()

Compares multiple specific sessions.

```python
result = await service.compare_sessions(
    session_ids=[uuid.UUID("..."), uuid.UUID("...")],
    include_invalid=False
)

# Returns dict with:
# - sessions: list of per-session metrics
# - summary: aggregated statistics
```

### get_experiment_comparison()

Convenience method that returns all comparison views in one call.

```python
result = await service.get_experiment_comparison(
    experiment_id=uuid.UUID("..."),
    include_invalid=False
)

# Returns ExperimentComparisonResult with:
# - experiment_id, experiment_name, generated_at
# - variants, providers, models, harness_profiles
```

## Summary View Queries

All summary view queries are available in `DashboardQueries` class:

- `variant_summary_valid_only()` - Variant-level summary
- `provider_summary_valid_only()` - Provider-level summary  
- `model_summary_valid_only()` - Model-level summary
- `harness_profile_summary_valid_only()` - Harness profile summary

All queries:
- Use parameterized placeholders (`:experiment_id`) for SQL injection prevention
- Exclude invalid sessions (`outcome_state != 'invalid'`)
- Have deterministic `ORDER BY` clauses

## Acceptance Criteria Evidence

### 1. Users can compare variants inside one experiment across key latency and error metrics

**Evidence**: `compare_variants()` method returns:
- `avg_latency_ms` - Average latency
- `avg_ttft_ms` - Average time to first token
- `total_errors` - Total error count
- `error_rate` - Error rate (errors/requests)
- `session_count` - Number of valid sessions
- `total_requests` - Total request count

### 2. Summary views exclude invalid sessions correctly

**Evidence**: All queries include filter:
```sql
AND (s.outcome_state IS NULL OR s.outcome_state != 'invalid')
```

This ensures:
- Sessions with `outcome_state = 'invalid'` are excluded
- Sessions with `outcome_state = 'valid'` are included
- Sessions with `outcome_state IS NULL` (not yet validated) are included

### 3. Result ordering and filtering are deterministic

**Evidence**: All queries have explicit `ORDER BY` clauses:
- `variant_summary_valid_only()`: `ORDER BY v.name ASC`
- `provider_summary_valid_only()`: `ORDER BY v.provider ASC`
- `model_summary_valid_only()`: `ORDER BY v.provider ASC, v.model_alias ASC`
- `harness_profile_summary_valid_only()`: `ORDER BY v.harness_profile ASC`

Service methods support `order_by` parameter with secondary sort keys for determinism.

## Test Coverage

Unit tests verify:
- Pydantic model instantiation and field validation
- Query string generation with correct parameterization
- Security: No string interpolation, only `:param` placeholders
- Invalid session filtering in query strings

## Files Modified

1. `src/reporting/comparison.py` - Comparison service implementation
2. `src/reporting/queries.py` - Summary view SQL queries
3. `tests/unit/test_reporting.py` - Unit tests for new functionality