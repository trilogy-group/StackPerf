# CLI Evidence for COE-320: Health Checks and Diagnostics

## Overview

This document demonstrates the new health check and diagnostics CLI commands that allow operators to verify stack health before launching benchmark sessions.

## 1. Health Check Command

### Command Help

```bash
$ benchmark health check --help

 Usage: benchmark health check [OPTIONS]

 Run health checks on all stack components.

 Checks database connectivity, LiteLLM proxy health, Prometheus metrics, and configuration validity. Returns exit code 0 if healthy, 1 if unhealthy.

 This command should be run before launching benchmark sessions to ensure all required services are available and properly configured.

╭─ Options ───────────────────────────────────────────────────────────────────────────────────╮
│ --configs-dir      -c      PATH  Directory containing config files [default: ./configs]    │
│ --json             -j            Output in JSON format                                     │
│ --help                           Show this message and exit.                                │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Example Output (with services not running)

```bash
$ benchmark health check

Running stack health checks...

                Health Check Results                 
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Component    ┃ Status       ┃ Message                                       ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ database     │ ✓ healthy    │ SQLite database connection successful        │
│ litellm_proxy│ ✗ unhealthy  │ Cannot connect to LiteLLM proxy at           │
│              │              │ http://localhost:4000                         │
│ prometheus   │ ✗ unhealthy  │ Cannot connect to Prometheus at               │
│              │              │ http://localhost:9090                         │
│ configurations│ ✓ healthy   │ Configuration files found                     │
└──────────────┴──────────────┴──────────────────────────────────────────────┘

✗ 2 check(s) unhealthy: litellm_proxy, prometheus
```

### Example Output (JSON format)

```bash
$ benchmark health check --json

{
  "status": "unhealthy",
  "summary": "2 check(s) unhealthy: litellm_proxy, prometheus",
  "checks": [
    {
      "name": "database",
      "status": "healthy",
      "message": "SQLite database connection successful",
      "details": {
        "database_type": "SQLite",
        "url": "sqlite:///./benchmark.db"
      },
      "suggestion": null
    },
    {
      "name": "litellm_proxy",
      "status": "unhealthy",
      "message": "Cannot connect to LiteLLM proxy at http://localhost:4000",
      "details": {},
      "suggestion": "Start LiteLLM proxy with 'docker-compose up -d litellm'"
    },
    {
      "name": "prometheus",
      "status": "unhealthy",
      "message": "Cannot connect to Prometheus at http://localhost:9090",
      "details": {},
      "suggestion": "Start Prometheus with 'docker-compose up -d prometheus'"
    },
    {
      "name": "configurations",
      "status": "healthy",
      "message": "Configuration files found",
      "details": {
        "providers": 2,
        "harnesses": 2,
        "variants": 3
      },
      "suggestion": null
    }
  ]
}
```

## 2. Diagnostics Command

### Command Help

```bash
$ benchmark health diagnose --help

 Usage: benchmark health diagnose [OPTIONS]

 Run comprehensive diagnostics on environment, configuration, and services.

 Provides detailed information about:
 - Environment variables and paths
 - Configuration files and their validity
 - Service connectivity and status

 Diagnostics point directly to failing configuration or service issues and provide actionable suggestions for resolution.

╭─ Options ───────────────────────────────────────────────────────────────────────────────────╮
│ --configs-dir      -c      PATH  Directory containing config files [default: ./configs]    │
│ --json             -j            Output in JSON format                                     │
│ --category         -C      TEXT  Filter to specific category (environment, configuration,  │
│                                services)                                                   │
│ --help                           Show this message and exit.                                │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
```

### Example Output

```bash
$ benchmark health diagnose

Running stack diagnostics...

          Environment Diagnostics           
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name                 ┃ Status   ┃ Message                                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ DATABASE_URL         │ warning  │ Using default SQLite database (./benchmark.db)│
│ LITELLM_MASTER_KEY   │ warning  │ LITELLM_MASTER_KEY not set                    │
│ LITELLM_BASE_URL     │ ✓ ok     │ LiteLLM proxy URL                             │
│ PROMETHEUS_URL       │ ✓ ok     │ Prometheus metrics URL                        │
│ CONFIGS_DIR          │ ✓ ok     │ Configuration directory exists at             │
│                      │          │ /Users/dev/StackPerf/configs                  │
│ CONFIGS_DIR_WRITE    │ ✓ ok     │ Write access to configuration directory       │
└──────────────────────┴──────────┴──────────────────────────────────────────────┘

         Configuration Diagnostics          
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name                 ┃ Status   ┃ Message                                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ providers            │ ✓ ok     │ 2 provider configuration(s) found            │
│ harnesses            │ ✓ ok     │ 2 harness configuration(s) found             │
│ variants             │ ✓ ok     │ 3 variant configuration(s) found             │
│ experiments          │ ✓ ok     │ 1 experiment configuration(s) found          │
│ task_cards           │ ✓ ok     │ 1 task card configuration(s) found           │
└──────────────────────┴──────────┴──────────────────────────────────────────────┘

            Services Diagnostics             
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name                 ┃ Status   ┃ Message                                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ database             │ ✓ ok     │ SQLite connected, 0 tables                    │
│ litellm_proxy        │ ✗ error  │ Cannot connect to LiteLLM proxy               │
│ prometheus           │ ✗ error  │ Cannot connect to Prometheus                  │
└──────────────────────┴──────────┴──────────────────────────────────────────────┘

✗ Found 2 error(s)
  • litellm_proxy: Cannot connect to LiteLLM proxy
    Suggestion: Start LiteLLM: docker-compose up -d litellm
  • prometheus: Cannot connect to Prometheus
    Suggestion: Start Prometheus: docker-compose up -d prometheus
```

### Category-Specific Diagnostics

```bash
$ benchmark health diagnose --category environment

Running stack diagnostics...

          Environment Diagnostics           
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name                 ┃ Status   ┃ Message                                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ DATABASE_URL         │ warning  │ Using default SQLite database (./benchmark.db)│
│ LITELLM_MASTER_KEY   │ warning  │ LITELLM_MASTER_KEY not set                    │
│ LITELLM_BASE_URL     │ ✓ ok     │ LiteLLM proxy URL                             │
│ PROMETHEUS_URL       │ ✓ ok     │ Prometheus metrics URL                        │
│ CONFIGS_DIR          │ ✓ ok     │ Configuration directory exists at             │
│                      │          │ /Users/dev/StackPerf/configs                  │
│ CONFIGS_DIR_WRITE    │ ✓ ok     │ Write access to configuration directory       │
└──────────────────────┴──────────┴──────────────────────────────────────────────┘
```

## 3. Key Features Demonstrated

### Operator-Friendly Error Messages

All error messages point directly to the failing configuration or service and provide actionable suggestions:

- **Missing LiteLLM**: "Cannot connect to LiteLLM proxy at http://localhost:4000" → "Start LiteLLM proxy with 'docker-compose up -d litellm'"
- **Missing Prometheus**: "Cannot connect to Prometheus at http://localhost:9090" → "Start Prometheus with 'docker-compose up -d prometheus'"
- **Missing configs**: "Configuration directory not found: ./configs" → "Create configuration directory at /path/to/configs"
- **No providers**: "No provider configurations found" → "Add at least one provider configuration file in configs/providers/"

### Exit Codes

- **Exit 0**: All health checks passing (healthy)
- **Exit 1**: One or more health checks failing (unhealthy or errors)

This allows operators to easily integrate the health check into automation scripts:

```bash
#!/bin/bash
# Pre-session health check
if benchmark health check; then
    echo "Stack is healthy, launching session..."
    benchmark session create ...
else
    echo "Stack health check failed, check diagnostics"
    benchmark health diagnose
    exit 1
fi
```

### JSON Output for Automation

The `--json` flag provides machine-readable output for integration with monitoring systems or CI/CD pipelines.

## 4. Acceptance Criteria Validation

✅ **Operators can verify stack health before launching a session**
- Single command: `benchmark health check`
- Clear pass/fail status with exit codes

✅ **Obvious misconfigurations are surfaced before benchmark traffic starts**
- Environment variables validated (DATABASE_URL, LITELLM_MASTER_KEY, etc.)
- Configuration directories and files checked
- Service connectivity verified

✅ **Diagnostics point directly to the failing configuration or service**
- Specific component names in all error messages
- Concrete remediation steps provided
- Category-based organization for focused troubleshooting