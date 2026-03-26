---
name: custom-codereview-guide
description: |
  Repository-specific code review guidance for StackPerf.
  This skill supplements the default OpenHands review skill with project-specific
  rules for reviewing Python code in a benchmarking/orchestration system.
---

# Custom Code Review Guide for StackPerf

## Project Context

StackPerf is a harness-agnostic benchmarking system:
- **LiteLLM Proxy**: Routes inference traffic, logs requests
- **Collectors**: Normalize LiteLLM and Prometheus data
- **Session Manager**: Issue credentials, track session lifecycle
- **Query API**: Compare benchmarks, export results
- **Grafana Dashboards**: Visualize performance comparisons

## Review Focus Areas

### 1. Async and Concurrency

**Watch for:**
- Missing `asyncio.run()` wrappers
- Blocking calls in async functions (use `run_in_executor`)
- Unbounded queues without backpressure
- Missing exception handling in `gather()`

**Good patterns:**
```python
# Use asyncio.Queue with maxsize
queue = asyncio.Queue(maxsize=100)

# Proper error handling
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 2. Error Handling

**Watch for:**
- Bare `except:` clauses
- Raising generic `Exception` instead of custom types
- Missing error context in logs
- Silent failures

**Good patterns:**
```python
class CollectorError(Exception):
    """Base error for collector operations."""

class NormalizationError(CollectorError):
    """Failed to normalize request data."""

# Context-rich errors
logger.error("failed to normalize request", extra={
    "request_id": request_id,
    "error": str(e),
})
```

### 3. Security

**Watch for:**
- API keys or secrets in logs
- SQL injection in query builders
- Path traversal in file operations
- Missing input validation

**Critical rules:**
- Never log `api_key` or `session_token`
- Validate all user inputs before use
- Use parameterized queries, never string formatting

### 4. Type Safety

**Watch for:**
- Missing type hints on public functions
- `Any` overuse
- Missing return type annotations
- Inconsistent Optional handling

**Good patterns:**
```python
from typing import Optional

def get_session(session_id: str) -> Optional[Session]:
    ...

# Use pydantic for validation
class BenchmarkConfig(BaseModel):
    model: str
    max_tokens: int = Field(ge=1, le=100000)
```

### 5. Testing

**Watch for:**
- Tests without assertions
- Missing edge case coverage
- Tests that depend on external services
- Missing cleanup in fixtures

**Good patterns:**
- Use `pytest-asyncio` for async tests
- Mock external services with `unittest.mock`
- Use `tmp_path` fixture for file tests
- Property-based testing with `hypothesis`

### 6. Performance

**Watch for:**
- N+1 query patterns
- Missing database indexes
- Inefficient data structures
- Memory leaks in long-running processes

## Documentation Requirements

Code changes should update:
- `docs/` for behavior changes
- `README.md` for usage changes
- `AGENTS.md` for repo-specific knowledge
- Docstrings for all public functions

## Evidence Requirements

PRs should include:
- **Behavior changes**: Test output showing before/after
- **Performance changes**: Benchmarks or timing data
- **New features**: Usage examples
- **Bug fixes**: Reproduction case and fix verification