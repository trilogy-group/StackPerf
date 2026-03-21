.PHONY: install dev lint test clean help

help:
	@echo "StackPerf Development Commands"
	@echo ""
	@echo "  install     Install production dependencies"
	@echo "  dev         Install dev dependencies"
	@echo "  lint        Run linters (ruff, mypy)"
	@echo "  test        Run all tests"
	@echo "  test-unit   Run unit tests only"
	@echo "  test-int    Run integration tests only"
	@echo "  clean       Remove build artifacts"
	@echo ""

install:
	uv sync

dev:
	uv sync --all-extras

lint:
	uv run ruff check src/ tests/
	uv run mypy src/

test:
	uv run pytest tests/ -v

test-unit:
	uv run pytest tests/unit/ -v

test-int:
	uv run pytest tests/integration/ -v

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf build/ dist/ *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
