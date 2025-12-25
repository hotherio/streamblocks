VENV := $(PWD)/.venv
PACKAGE := 'streamblocks'

.PHONY: help install install-dev install-docs test coverage lint format type-check docs clean build package check-dist changelog

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation targets
install: ## Install production dependencies
	uv sync

install-dev: ## Install development dependencies and git hooks
	uv sync --group dev
	. $(VENV)/bin/activate && lefthook install

install-docs: ## Install documentation dependencies
	uv sync --group doc

install-all: ## Install all dependencies (dev + docs + extras)
	uv sync --group dev --group doc --all-extras

# Testing targets
test: ## Run tests
	uv run pytest

coverage: ## Run tests with coverage report
	uv run pytest --cov=hother.streamblocks --cov-report=term-missing --cov-report=html

coverage-check: ## Run tests and fail if coverage is below threshold
	uv run pytest --cov=hother.streamblocks --cov-fail-under=90

# Code quality targets
lint: ## Run pre-commit hooks on all files
	uv run lefthook run pre-commit --all-files -- --no-stash

format: ## Format code with ruff
	uv run ruff format src tests examples

type-check: ## Run type checking with basedpyright
	uv run basedpyright src

check: lint type-check test ## Run all quality checks

# Examples
examples: ## Run all examples (skip API-dependent ones)
	uv run python examples/run_examples.py --skip-api

# Documentation targets
docs: ## Serve documentation locally
	uv run mkdocs serve

docs-build: ## Build documentation
	uv run mkdocs build

# Build targets
build: clean-build ## Build package
	uv build

package: build ## Alias for build

check-dist: build ## Check distribution for PyPI compatibility
	uv run twine check dist/*

# Changelog targets
changelog: ## Generate full changelog
	git-cliff -o CHANGELOG.md

changelog-unreleased: ## Preview unreleased changes
	@git-cliff --unreleased

changelog-latest: ## Get changelog for latest tag
	@git-cliff --latest --strip header

# Version management
version: ## Show current version
	@echo "Current version: $$(grep -m1 'version = ' pyproject.toml | cut -d'\"' -f2)"

# Clean targets
clean: clean-build clean-pyc clean-coverage ## Remove all build artifacts

clean-build: ## Remove build artifacts
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

clean-pyc: ## Remove Python compiled files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

clean-coverage: ## Remove coverage artifacts
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf coverage.json
