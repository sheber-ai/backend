.DEFAULT_GOAL := help
.PHONY: help install dev db-create seed migration migrate downgrade check-migrations lint format typecheck test openapi

help: ## Show commands
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install deps and git hooks
	uv sync
	uv run pre-commit install

dev: ## Run API with reload on :8000
	uv run uvicorn main:app --reload --port 8000

db-create: ## Create role and databases in local PostgreSQL (asks for the postgres password)
	psql -h $${DB_HOST:-localhost} -U postgres -v ON_ERROR_STOP=1 -f scripts/create_db.sql

seed: ## Load reference data (cities); safe to run again
	uv run python -m scripts.seed

migration: ## Autogenerate migration: make migration m="add listings table"
	@test -n "$(m)" || (echo 'Usage: make migration m="add listings table"' && exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

migrate: ## Apply migrations
	uv run alembic upgrade head

downgrade: ## Roll back last migration
	uv run alembic downgrade -1

check-migrations: ## Check models match migrations
	uv run alembic check

lint: ## Lint, format check, type check
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .

format: ## Format code
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## Type check only
	uv run mypy .

test: ## Run tests (db tests need make db-create)
	uv run pytest

openapi: ## Export OpenAPI schema to openapi.json
	uv run python -m scripts.export_openapi > openapi.json
