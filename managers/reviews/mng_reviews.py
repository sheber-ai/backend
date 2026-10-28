from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from managers.mng_base import BaseManager
from models.reviews.mdl_review import Review


class ReviewManager(BaseManager[Review]):
    model = Review

    async def get_by_order(self, order_id: UUID) -> Review | None:
        return await self._session.scalar(select(Review).where(Review.order_id == order_id))

    async def list_by_workshop(self, workshop_id: UUID, *, offset: int, limit: int) -> tuple[Sequence[Review], int]:
        condition = Review.workshop_id == workshop_id
        total = await self._session.scalar(select(func.count()).select_from(Review).where(condition)) or 0
        items = await self._session.scalars(
            select(Review)
            .where(condition)
            .options(selectinload(Review.client))
            .order_by(Review.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return items.all(), total

    async def summary(self, workshop_id: UUID) -> tuple[int, float | None]:
        row = (
            await self._session.execute(
                select(func.count(), func.avg(Review.rating)).where(Review.workshop_id == workshop_id)
            )
        ).one()
        count, average = row
        return int(count), float(average) if average is not None else None
