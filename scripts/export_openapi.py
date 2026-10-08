"""Print the OpenAPI schema without starting the server."""

import json
import sys

from rest_api.start_app import create_app

if __name__ == "__main__":
    json.dump(create_app().openapi(), sys.stdout, ensure_ascii=False, indent=2)
