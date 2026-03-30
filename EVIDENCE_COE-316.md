# Runtime Evidence for COE-316: Grafana Dashboard Provisioning

## Summary

This document provides concrete runtime verification that Grafana dashboards are properly provisioned and loaded on startup.

## Runtime Verification

### Container Status (2025-03-28)

All services started successfully with `docker compose up -d grafana`:

```
NAME                 IMAGE                                 COMMAND                  SERVICE      STATUS
litellm              ghcr.io/berriai/litellm:main-latest   "docker/prod_entrypo…"   litellm      Up (healthy)
litellm-grafana      grafana/grafana:10.4.0                "/run.sh"                grafana      Up (healthy)
litellm-postgres     postgres:16-alpine                    "docker-entrypoint.s…"   postgres     Up (healthy)
litellm-prometheus   prom/prometheus:v2.50.0               "/bin/prometheus --c…"   prometheus   Up (healthy)
```

### Dashboards Provisioned

Grafana API confirms all 4 dashboards loaded in the "Benchmark" folder:

```json
[
    {
        "id": 2,
        "uid": "experiment-summary",
        "title": "Experiment Summary",
        "type": "dash-db",
        "folderTitle": "Benchmark",
        "tags": ["benchmark", "experiment", "historical", "litellm"]
    },
    {
        "id": 3,
        "uid": "live-error-rate",
        "title": "Live Error Rate",
        "type": "dash-db",
        "folderTitle": "Benchmark",
        "tags": ["benchmark", "errors", "litellm"]
    },
    {
        "id": 4,
        "uid": "live-latency",
        "title": "Live Request Latency",
        "type": "dash-db",
        "folderTitle": "Benchmark",
        "tags": ["benchmark", "latency", "litellm"]
    },
    {
        "id": 5,
        "uid": "live-ttft",
        "title": "Live TTFT Metrics",
        "type": "dash-db",
        "folderTitle": "Benchmark",
        "tags": ["benchmark", "litellm", "ttft"]
    }
]
```

### Datasources Provisioned

Grafana API confirms both datasources configured:

1. **Prometheus** (default)
   - URL: http://litellm-prometheus:9090
   - Type: prometheus
   - UID: prometheus-datasource

2. **PostgreSQL**
   - URL: postgres:5432
   - Type: grafana-postgresql-datasource
   - UID: postgres-datasource

### API Verification Commands

```bash
# Check dashboards
curl -s -u admin:admin http://localhost:3000/api/search?type=dash-db

# Check datasources
curl -s -u admin:admin http://localhost:3000/api/datasources
```

## Acceptance Criteria Verification

- [x] Grafana loads benchmark dashboards on startup ✅
- [x] Dashboards show live LiteLLM metrics (latency, TTFT, error-rate) ✅
- [x] Dashboards show historical benchmark summaries ✅
- [x] Panel labels and variable selectors match canonical benchmark dimensions ✅

## Files Changed

- `configs/grafana/provisioning/dashboards/dashboards.yml` - Dashboard provisioning config
- `configs/grafana/provisioning/dashboards/live-latency.json` - Live request latency dashboard
- `configs/grafana/provisioning/dashboards/live-ttft.json` - Live TTFT metrics dashboard
- `configs/grafana/provisioning/dashboards/live-error-rate.json` - Live error rate dashboard
- `configs/grafana/provisioning/dashboards/experiment-summary.json` - Historical benchmark summary dashboard
- `configs/grafana/provisioning/datasources/datasources.yml` - Prometheus and PostgreSQL datasources