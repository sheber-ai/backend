from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import CityNotFoundError
from common.i18n import localize
from enums.i18n_enum import LanguageEnum
from managers.cities.mng_cities import CityManager
from models.cities.mdl_city import City
from schemas.cities.sch_city import CitySchema, CitySeedSchema
from schemas.sch_base import PageSchema, language_context


class CityService:
    def __init__(self, session: AsyncSession, mng_cities: CityManager) -> None:
        self._session = session
        self._mng_cities = mng_cities

    async def list_cities(self, language: LanguageEnum) -> PageSchema[CitySchema]:
        cities = sorted(
            await self._mng_cities.list_active(),
            key=lambda city: (city.sort_order, localize(city.name, language)),
        )
        items = [CitySchema.model_validate(city, context=language_context(language)) for city in cities]
        return PageSchema(items=items, total=len(items))

    async def require_active(self, city_id: UUID) -> City:
        city = await self._mng_cities.get_active(city_id)
        if city is None:
            raise CityNotFoundError(f"City {city_id} not found")
        return city

    async def require_all_active(self, city_ids: Sequence[UUID]) -> list[City]:
        """The cities in the given order, without repeats; any unknown or hidden one fails the whole list."""
        unique = list(dict.fromkeys(city_ids))
        found = {city.id: city for city in await self._mng_cities.list_active_by_ids(unique)}
        missing = [city_id for city_id in unique if city_id not in found]
        if missing:
            raise CityNotFoundError(f"City {missing[0]} not found")
        return [found[city_id] for city_id in unique]

    async def seed_cities(self, cities: Sequence[CitySeedSchema]) -> int:
        for city in cities:
            await self._mng_cities.upsert(
                slug=city.slug, name=city.name.model_dump(by_alias=False, exclude_none=True), sort_order=city.sort_order
            )
        await self._session.commit()
        return len(cities)
