.DEFAULT_GOAL := help
.PHONY: help install dev db-up db-down migration migrate downgrade check-migrations lint format typecheck test openapi

help: ## Список команд
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Зависимости + git-хуки
	uv sync
	uv run pre-commit install

dev: ## API с автоперезагрузкой на :8000
	uv run uvicorn main:app --reload --port 8000

db-up: ## Поднять PostgreSQL в Docker
	docker compose up -d db

db-down: ## Остановить PostgreSQL
	docker compose down

migration: ## Новая миграция из моделей: make migration m="add listings table"
	@test -n "$(m)" || (echo 'Укажите описание: make migration m="add listings table"' && exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

migrate: ## Применить миграции
	uv run alembic upgrade head

downgrade: ## Откатить последнюю миграцию
	uv run alembic downgrade -1

check-migrations: ## Модели и миграции совпадают
	uv run alembic check

lint: ## Линтер + проверка форматирования + типы
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy .

format: ## Автоформатирование
	uv run ruff check --fix .
	uv run ruff format .

typecheck: ## Только mypy
	uv run mypy .

test: ## Все тесты (db-тестам нужен make db-up)
	uv run pytest

openapi: ## Выгрузить OpenAPI-схему в openapi.json (без запуска сервера)
	uv run python -m scripts.export_openapi > openapi.json
