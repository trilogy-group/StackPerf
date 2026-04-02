# COE-313: Evidence for Query API Implementation

## Summary

This document provides evidence that the Query API for experiments, variants, sessions, requests, and rollups is working correctly.

## API Server Startup

```bash
$ AUTO_CREATE_TABLES=true uvicorn api.main:app --host 0.0.0.0 --port 8000
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Endpoint Verification

### 1. Health Check

```bash
$ curl http://localhost:8000/health
{"status":"ok"}
```

### 2. List Experiments

```bash
$ curl http://localhost:8000/experiments
{
  "total": 0,
  "limit": 100,
  "offset": 0,
  "items": []
}
```

### 3. Get Experiment by ID (404 when not found)

```bash
$ curl -i http://localhost:8000/experiments/00000000-0000-0000-0000-000000000000
HTTP/1.1 404 Not Found
{"detail":"Experiment not found"}
```

### 4. List Variants with Filter

```bash
$ curl "http://localhost:8000/variants?provider=openai"
{
  "total": 0,
  "limit": 100,
  "offset": 0,
  "items": []
}

$ curl "http://localhost:8000/variants?harness_profile=default"
{
  "total": 0,
  "limit": 100,
  "offset": 0,
  "items": []
}
```

### 5. List Sessions with Filters

```bash
$ curl "http://localhost:8000/sessions?status=active"
{
  "total": 0,
  "limit": 100,
  "offset": 0,
  "items": []
}

$ curl "http://localhost:8000/sessions?experiment_id=550e8400-e29b-41d4-a716-446655440000"
{
  "total": 0,
  "limit": 100,
  "offset": 0,
  "items": []
}
```

### 6. List Requests with Filters

```bash
$ curl "http://localhost:8000/requests?provider=openai"
{
  "total": 0,
  "limit": 100,
  "offset": 0,
  "items": []
}

$ curl "http://localhost:8000/requests?error=false"
{
  "total": 0,
  "limit": 100,
  "offset": 0,
  "items": []
}

$ curl "http://localhost:8000/requests?cache_hit=true"
{
  "total": 0,
  "limit": 100,
  "offset": 0,
  "items": []
}
```

### 7. List Metric Rollups with Filters

```bash
$ curl "http://localhost:8000/rollups?dimension_type=session"
{
  "total": 0,
  "limit": 100,
  "offset": 0,
  "items": []
}

$ curl "http://localhost:8000/rollups?metric_name=avg_latency_ms"
{
  "total": 0,
  "limit": 100,
  "offset": 0,
  "items": []
}
```

### 8. Pagination

```bash
$ curl "http://localhost:8000/experiments?limit=10&offset=0"
{
  "total": 0,
  "limit": 10,
  "offset": 0,
  "items": []
}
```

### 9. UUID Validation

```bash
$ curl -i http://localhost:8000/experiments/not-a-uuid
HTTP/1.1 422 Unprocessable Entity
{
  "detail": [
    {
      "type": "uuid_parsing",
      "loc": ["path", "experiment_id"],
      "msg": "Input should be a valid UUID",
      "input": "not-a-uuid"
    }
  ]
}
```

## OpenAPI Documentation

The API provides interactive documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Test Coverage

All 31 unit tests pass:

```bash
$ python -m pytest tests/unit/test_api.py -v
tests/unit/test_api.py::test_import_api_package PASSED
tests/unit/test_api.py::test_import_main_app PASSED
tests/unit/test_api.py::test_import_schemas PASSED
tests/unit/test_api.py::TestSchemas::test_experiment_response_schema PASSED
tests/unit/test_api.py::TestSchemas::test_variant_response_schema PASSED
tests/unit/test_api.py::TestSchemas::test_session_response_schema PASSED
tests/unit/test_api.py::TestSchemas::test_request_response_schema PASSED
tests/unit/test_api.py::TestSchemas::test_metric_rollup_response_schema PASSED
tests/unit/test_api.py::TestSchemas::test_paginated_response_schema PASSED
tests/unit/test_api.py::TestSchemas::test_session_detail_response PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_health_check PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_list_experiments_empty PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_list_experiments_with_data PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_get_experiment_not_found PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_list_variants_empty PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_list_variants_with_filter PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_get_variant_not_found PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_list_sessions_empty PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_list_sessions_with_experiment_filter PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_get_session_not_found PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_list_requests_empty PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_list_requests_with_session_filter PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_get_request_not_found PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_list_rollups_empty PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_list_rollups_with_filter PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_get_rollup_not_found PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_get_experiment_comparison_not_found PASSED
tests/unit/test_api.py::TestAPIEndpoints::test_legacy_metrics_endpoint PASSED
tests/unit/test_api.py::TestQueryParameters::test_pagination_limit_validation PASSED
tests/unit/test_api.py::TestQueryParameters::test_pagination_offset_validation PASSED
tests/unit/test_api.py::TestQueryParameters::test_uuid_validation PASSED
============================== 31 passed in 0.31s ==============================
```

## Acceptance Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Core benchmark entities queryable by ID | ✅ PASS | GET endpoints for all entities: /experiments/{id}, /variants/{id}, /sessions/{id}, /requests/{id}, /rollups/{id} |
| Core benchmark entities queryable by filter | ✅ PASS | Filter parameters on all list endpoints (provider, status, dimension_type, etc.) |
| Request views expose canonical fields | ✅ PASS | RequestResponse schema includes: id, request_id, session_id, provider, model, timestamp, latency_ms, ttft_ms, tokens, error, cache_hit |
| Session views expose canonical fields | ✅ PASS | SessionResponse schema includes: id, experiment_id, variant_id, task_card_id, harness_profile, git metadata, timestamps |
| API contracts documented | ✅ PASS | OpenAPI docs available at /docs, /redoc, /openapi.json |
| API test-covered | ✅ PASS | 31 unit tests covering all endpoints, schemas, and validation |

---

**Generated:** 2026-03-27T18:00:00Z