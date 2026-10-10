.DEFAULT_GOAL := help

.PHONY: help install dev start test test-v db-info clean

help: ## Show this help message
	@echo "Available commands:"
	@echo "  make install    - Install and sync dependencies with uv"
	@echo "  make dev        - Start local FastAPI development server with auto-reload (port 8000)"
	@echo "  make test       - Run automated pytest test suite"
	@echo "  make test-v     - Run automated pytest test suite with verbose output"
	@echo "  make db-info    - Inspect DuckDB story counts and active database path"
	@echo "  make clean      - Clean temporary caches (__pycache__, .pytest_cache)"

install: ## Sync dependencies with uv
	uv sync

dev: ## Start FastAPI dev server (port 8000)
	uv run uvicorn main:app --reload --port 8000

start: dev ## Alias for dev

test: ## Run test suite
	uv run pytest

test-v: ## Run test suite with verbose output
	uv run pytest -v

db-info: ## Display DuckDB story counts and status
	uv run python -c "import database; p = database.get_db_path(); s, l = database.counts(); print(f'Database Path: {p}'); print(f'Stories: {s} | Lab Stories: {l}')"

clean: ## Remove __pycache__ and pytest cache directories
	uv run python -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; shutil.rmtree('.pytest_cache', ignore_errors=True)"
