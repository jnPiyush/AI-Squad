# Makefile for AI-Squad development

.PHONY: help install install-dev test lint format clean docs build publish

help:  ## Show this help message
	@echo "AI-Squad Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install AI-Squad
	pip install -e .

install-dev:  ## Install with development dependencies
	pip install -e ".[dev,docs]"

test:  ## Run tests
	pytest tests/

test-cov:  ## Run tests with coverage
	pytest --cov=ai_squad --cov-report=html --cov-report=term-missing tests/

lint:  ## Run linting
	ruff check ai_squad/
	mypy ai_squad/

format:  ## Format code
	black ai_squad/ tests/
	ruff check ai_squad/ --fix

clean:  ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/ site/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docs:  ## Build documentation
	mkdocs build

docs-serve:  ## Serve documentation locally
	mkdocs serve

build:  ## Build distribution packages
	python -m build

publish-test:  ## Publish to TestPyPI
	python -m twine upload --repository testpypi dist/*

publish:  ## Publish to PyPI
	python -m twine upload dist/*

init-dev:  ## Initialize development environment
	python -m venv venv
	. venv/bin/activate && pip install -e ".[dev,docs]"
	pre-commit install
	@echo "Development environment ready! Activate with: source venv/bin/activate"

check:  ## Run all checks (lint, test, coverage)
	@echo "Running linting..."
	@make lint
	@echo "\nRunning tests..."
	@make test-cov
	@echo "\nAll checks passed!"

.DEFAULT_GOAL := help
