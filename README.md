# Sheber Backend

REST API платформы Sheber. Правила, структура и соглашения — в [AGENTS.md](AGENTS.md).

## Быстрый старт

```bash
cp .env.example .env
make install
make db-up
(cd ../keycloak-theme && make up)   # Keycloak на :8080
make migrate
make dev
```

Swagger: http://localhost:8000/api/docs · OpenAPI: http://localhost:8000/api/v1/openapi.json
