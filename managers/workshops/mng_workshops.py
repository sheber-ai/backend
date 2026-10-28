from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from enums.workshops_enum import WorkshopStatusEnum
from managers.mng_base import BaseManager
from models.workshops.mdl_workshop import Workshop
from models.workshops.mdl_workshop_city import WorkshopCity


class WorkshopManager(BaseManager[Workshop]):
    model = Workshop

    async def get_by_owner(self, owner_id: UUID) -> Workshop | None:
        return await self._session.scalar(
            select(Workshop)
            .where(Workshop.owner_id == owner_id)
            .options(selectinload(Workshop.city))
            .execution_options(populate_existing=True)
        )

    async def get_with_city(self, workshop_id: UUID) -> Workshop | None:
        return await self._session.scalar(
            select(Workshop)
            .where(Workshop.id == workshop_id)
            .options(selectinload(Workshop.city))
            .execution_options(populate_existing=True)
        )

    async def list_with_owner(self, *, status: str | None, offset: int, limit: int) -> tuple[Sequence[Workshop], int]:
        query = select(Workshop)
        if status is not None:
            query = query.where(Workshop.status == status)
        total = await self._session.scalar(select(func.count()).select_from(query.subquery())) or 0
        items = await self._session.scalars(
            query.options(selectinload(Workshop.owner), selectinload(Workshop.city))
            .order_by(Workshop.created_at)
            .offset(offset)
            .limit(limit)
        )
        return items.all(), total

    async def owner_ids(self, workshop_ids: Sequence[UUID]) -> list[UUID]:
        if not workshop_ids:
            return []
        rows = await self._session.scalars(select(Workshop.owner_id).where(Workshop.id.in_(workshop_ids)))
        return list(rows.all())

    async def owner_ids_for_order(self, *, city_id: UUID, furniture_type: str, exclude_owner_id: UUID) -> list[UUID]:
        """Owners of approved workshops that serve the city and make the furniture type."""
        serves_city = or_(
            Workshop.city_id == city_id,
            Workshop.id.in_(select(WorkshopCity.workshop_id).where(WorkshopCity.city_id == city_id)),
        )
        rows = await self._session.scalars(
            select(Workshop.owner_id).where(
                Workshop.status == WorkshopStatusEnum.APPROVED,
                Workshop.owner_id != exclude_owner_id,
                Workshop.furniture_types.contains([furniture_type]),
                serves_city,
            )
        )
        return list(rows.all())

    async def list_with_city(self, workshop_ids: Sequence[UUID]) -> Sequence[Workshop]:
        if not workshop_ids:
            return []
        items = await self._session.scalars(
            select(Workshop).where(Workshop.id.in_(workshop_ids)).options(selectinload(Workshop.city))
        )
        return items.all()
