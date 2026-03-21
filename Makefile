# StackPerf Makefile
# CI-aligned commands for local development

.PHONY: help sync lint type test check ci clean build

# Default target
help:
	@echo "StackPerf Development Commands"
	@echo "==============================="
	@echo ""
	@echo "Setup & Sync:"
	@echo "  sync       Sync dependencies with uv"
	@echo "  clean      Remove build artifacts and caches"
	@echo ""
	@echo "Quality Gates:"
	@echo "  lint       Run ruff linter"
	@echo "  type       Run mypy type checker"
	@echo "  test       Run pytest test suite"
	@echo "  check      Run all quality gates (lint + type + test)"
	@echo "  ci         Run full CI pipeline (same as check)"
	@echo ""
	@echo "Build:"
	@echo "  build      Build distribution packages"
	@echo ""

# Setup & Sync
sync:
	uv sync --all-extras

# Quality Gates
lint:
	uv run ruff check src/ tests/

lint-fix:
	uv run ruff check --fix src/ tests/

format:
	uv run ruff format src/ tests/

format-check:
	uv run ruff format --check src/ tests/

type:
	uv run mypy src/

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ --cov=src --cov-report=term-missing

# Full CI pipeline (runs all checks)
check: lint type test
	@echo "All quality gates passed ✓"

ci: check
	@echo "CI pipeline completed ✓"

# Build
build:
	uv build

# Clean
clean:
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
