# Sheber Backend

REST API платформы Sheber. Правила, структура и соглашения — в [AGENTS.md](AGENTS.md).

## Быстрый старт

Нужны локальный PostgreSQL 18 (Homebrew: `brew install postgresql@18`), [uv](https://docs.astral.sh/uv/) и Docker для Keycloak.

```bash
cp .env.example .env
make install
make db-create                       # роль sheber и базы sheber, sheber_test (спросит пароль postgres)
(cd ../keycloak-theme && make up)    # Keycloak на :8080
make migrate
make seed                            # справочники: города
make dev
```

Swagger: http://localhost:8000/api/docs · OpenAPI: http://localhost:8000/api/v1/openapi.json

Модерация мастерских выдаёт роль `contractor` через Admin API Keycloak (service account `sheber-backend`,
секрет в `.env`). Если realm создан до появления этого клиента — пересоздайте его: `cd ../keycloak-theme && make reset`.
