from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from managers.mng_base import BaseManager
from models.cities.mdl_city import City


class CityManager(BaseManager[City]):
    model = City

    async def list_active(self) -> Sequence[City]:
        items = await self._session.scalars(select(City).where(City.is_active).order_by(City.sort_order, City.slug))
        return items.all()

    async def list_active_by_ids(self, city_ids: Sequence[UUID]) -> Sequence[City]:
        items = await self._session.scalars(select(City).where(City.id.in_(city_ids), City.is_active))
        return items.all()

    async def get_active(self, city_id: UUID) -> City | None:
        return await self._session.scalar(select(City).where(City.id == city_id, City.is_active))

    async def upsert(self, *, slug: str, name: dict[str, Any], sort_order: int) -> None:
        statement = insert(City).values(slug=slug, name=name, sort_order=sort_order)
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[City.slug],
                set_={"name": statement.excluded.name, "sort_order": statement.excluded.sort_order},
            )
        )
