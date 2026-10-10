.DEFAULT_GOAL := help

.PHONY: help setup install setup-backend backend-install setup-extension extension-install backend-dev dev-backend run dev extension-dev dev-extension build-extension extension-build build test test-v backend-test db-info clean


help: ## Display available make commands
	@echo "========================================================================"
	@echo " News Bias Summarizer - Global Project Makefile"
	@echo "========================================================================"
	@echo "Setup Commands:"
	@echo "  make setup              - Install all dependencies (Backend + Extension)"
	@echo "  make setup-backend      - Install Backend dependencies with uv"
	@echo "  make setup-extension    - Install Chrome Extension dependencies with pnpm"
	@echo ""
	@echo "Development Commands:"
	@echo "  make run / backend-dev  - Start FastAPI backend with reload (http://localhost:8000)"
	@echo "  make extension-dev      - Start Chrome Extension in WXT development mode (pnpm dev)"
	@echo "  make extension-build    - Build Chrome Extension for production (pnpm build)"
	@echo ""
	@echo "Testing & Database:"
	@echo "  make test               - Run Backend automated test suite (pytest)"
	@echo "  make test-v             - Run Backend automated test suite with verbose output"
	@echo "  make db-info            - Inspect DuckDB active path and story counts"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean              - Clean pycache, pytest cache, and extension build artifacts"
	@echo "========================================================================"

# -------------------------------------------------------------------------
# Setup & Installation
# -------------------------------------------------------------------------

setup: setup-backend setup-extension ## Install all dependencies (Backend + Extension)

install: setup ## Alias for setup

setup-backend: ## Install backend dependencies with uv
	cd backend && uv sync

backend-install: setup-backend ## Alias for setup-backend

setup-extension: ## Install extension dependencies with pnpm
	cd extension && pnpm install

extension-install: setup-extension ## Alias for setup-extension

# -------------------------------------------------------------------------
# Running & Development
# -------------------------------------------------------------------------

backend-dev: ## Run FastAPI backend on port 8000
	cd backend && uv run uvicorn main:app --reload --port 8000

dev-backend: backend-dev ## Alias for backend-dev
run: backend-dev ## Alias for backend-dev
dev: backend-dev ## Alias for backend-dev

extension-dev: ## Run extension dev server (WXT with pnpm)
	cd extension && pnpm dev

dev-extension: extension-dev ## Alias for extension-dev

extension-build: ## Build extension bundle (chrome-mv3 with pnpm)
	cd extension && pnpm build

build-extension: extension-build ## Alias for extension-build
build: extension-build ## Alias for extension-build

# -------------------------------------------------------------------------
# Testing & Database
# -------------------------------------------------------------------------

test: ## Run backend automated test suite
	cd backend && uv run pytest

test-v: ## Run backend automated test suite with verbose output
	cd backend && uv run pytest -v

backend-test: test ## Alias for test

db-info: ## Display DuckDB story counts and status
	cd backend && uv run python -c "import database; p = database.get_db_path(); s, l = database.counts(); print(f'Database Path: {p}'); print(f'Stories: {s} | Lab Stories: {l}')"

# -------------------------------------------------------------------------
# Cleanup
# -------------------------------------------------------------------------

clean: ## Clean build artifacts and temporary caches
	cd backend && uv run python -c "import pathlib, shutil; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]; shutil.rmtree('.pytest_cache', ignore_errors=True)"
	cd backend && uv run python -c "import pathlib, shutil; shutil.rmtree('extension/.output', ignore_errors=True); shutil.rmtree('extension/.wxt', ignore_errors=True)"
