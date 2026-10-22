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

    async def seed_cities(self, cities: Sequence[CitySeedSchema]) -> int:
        for city in cities:
            await self._mng_cities.upsert(
                slug=city.slug, name=city.name.model_dump(by_alias=False, exclude_none=True), sort_order=city.sort_order
            )
        await self._session.commit()
        return len(cities)
