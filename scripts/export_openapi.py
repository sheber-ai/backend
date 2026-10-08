"""Печатает OpenAPI-схему без запуска сервера: `uv run python -m scripts.export_openapi > openapi.json`."""

import json
import sys

from rest_api.start_app import create_app

if __name__ == "__main__":
    json.dump(create_app().openapi(), sys.stdout, ensure_ascii=False, indent=2)
