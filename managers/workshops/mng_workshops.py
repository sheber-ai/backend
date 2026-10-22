from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from managers.mng_base import BaseManager
from models.workshops.mdl_workshop import Workshop


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
