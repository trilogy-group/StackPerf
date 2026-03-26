.PHONY: help install install-dev sync lint format type-check test test-cov clean all quality

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install production dependencies with uv
	@echo "Installing production dependencies..."
	uv pip install -e .

install-dev: ## Install all dependencies including dev tools with uv
	@echo "Installing development dependencies..."
	uv pip install -e ".[dev]"

sync: ## Sync dependencies from pyproject.toml using uv
	@echo "Syncing dependencies..."
	uv pip sync pyproject.toml
	uv pip install -e ".[dev]"

# Code quality
lint: ## Run ruff linter
	@echo "Running linter..."
	ruff check src tests

format: ## Run ruff formatter
	@echo "Running formatter..."
	ruff format src tests

format-check: ## Check formatting without modifying files
	@echo "Checking formatting..."
	ruff format --check src tests

type-check: ## Run mypy type checker
	@echo "Running type checker..."
	mypy src

# Testing
test: ## Run all tests
	@echo "Running tests..."
	pytest tests/ -v

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	pytest tests/unit -v

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	pytest tests/integration -v

test-cov: ## Run tests with coverage report
	@echo "Running tests with coverage..."
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

# Combined quality checks
quality: lint type-check test ## Run full quality check (lint + type-check + test)

# Build and clean
clean: ## Clean build artifacts and cache files
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Development utilities
dev-setup: ## Complete setup for new development environment
	@echo "Setting up development environment..."
	@make install-dev
	@echo "Development environment ready!"

dev-check: ## Quick check before committing
	@echo "Running pre-commit checks..."
	@make format-check
	@make lint
	@make type-check
	@make test-unit
