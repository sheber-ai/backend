# Sheber Backend

REST API платформы Sheber. Правила, структура и соглашения — в [AGENTS.md](AGENTS.md).

## Быстрый старт

```bash
cp .env.example .env
make install
make db-up
make migrate
make dev
```

Swagger: http://localhost:8000/api/docs · OpenAPI: http://localhost:8000/api/v1/openapi.json
