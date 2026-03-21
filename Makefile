.PHONY: help install sync lint type-check test quality clean compose-up compose-down compose-logs db-migrate db-reset

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies with uv
	uv sync

sync: install ## Alias for install

lint: ## Run ruff linting
	uv run ruff check src tests

type-check: ## Run mypy type checking
	uv run mypy src

test: ## Run tests
	uv run pytest tests

test-cov: ## Run tests with coverage
	uv run pytest tests --cov=src --cov-report=term-missing

quality: lint type-check test ## Run all quality checks (lint, type-check, test)

clean: ## Clean build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true

compose-up: ## Start local infrastructure stack
	docker compose up -d

compose-down: ## Stop local infrastructure stack
	docker compose down

compose-logs: ## Show infrastructure logs
	docker compose logs -f

compose-ps: ## Show infrastructure status
	docker compose ps

db-migrate: ## Run database migrations
	@echo "TODO: implement migrations"

db-reset: ## Reset database
	@echo "TODO: implement db reset"

db-shell: ## Open database shell
	docker compose exec postgres psql -U stackperf -d stackperf
