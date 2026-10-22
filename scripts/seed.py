"""Loads reference data from scripts/seeds/*.json. Idempotent: rows are upserted by slug."""

import asyncio
from pathlib import Path

from pydantic import TypeAdapter

from models import import_all_models
from schemas.cities.sch_city import CitySeedSchema
from services.cities.svc_cities import CityService
from services.di.container import create_container

SEEDS = Path(__file__).parent / "seeds"


async def main() -> None:
    import_all_models()
    cities = TypeAdapter(list[CitySeedSchema]).validate_json((SEEDS / "cities.json").read_text())
    async with create_container() as container, container.context() as context:
        svc_cities = await context.resolve(CityService)
        count = await svc_cities.seed_cities(cities)
    print(f"Cities: {count}")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
