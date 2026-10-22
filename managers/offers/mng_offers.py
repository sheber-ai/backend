from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from enums.offers_enum import OfferStatusEnum
from managers.mng_base import BaseManager
from models.offers.mdl_offer import Offer
from models.orders.mdl_order import Order
from models.workshops.mdl_workshop import Workshop

ACTIVE_STATUSES = (OfferStatusEnum.PENDING, OfferStatusEnum.ACCEPTED)


class OfferManager(BaseManager[Offer]):
    model = Offer

    async def get_with_order(self, offer_id: UUID) -> Offer | None:
        return await self._session.scalar(select(Offer).where(Offer.id == offer_id).options(selectinload(Offer.order)))

    async def get_for_workshop(self, order_id: UUID, workshop_id: UUID) -> Offer | None:
        return await self._session.scalar(
            select(Offer).where(Offer.order_id == order_id, Offer.workshop_id == workshop_id)
        )

    async def list_by_order(self, order_id: UUID) -> Sequence[Offer]:
        items = await self._session.scalars(
            select(Offer)
            .where(Offer.order_id == order_id, Offer.status != OfferStatusEnum.WITHDRAWN)
            .options(selectinload(Offer.workshop).selectinload(Workshop.city))
            .order_by(Offer.created_at)
        )
        return items.all()

    async def list_by_workshop(self, workshop_id: UUID, *, offset: int, limit: int) -> tuple[Sequence[Offer], int]:
        condition = Offer.workshop_id == workshop_id
        total = await self._session.scalar(select(func.count()).where(condition)) or 0
        items = await self._session.scalars(
            select(Offer)
            .where(condition)
            .options(selectinload(Offer.order).selectinload(Order.city))
            .order_by(Offer.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return items.all(), total

    async def count_active_by_orders(self, order_ids: Sequence[UUID]) -> dict[UUID, int]:
        if not order_ids:
            return {}
        rows = await self._session.execute(
            select(Offer.order_id, func.count())
            .where(Offer.order_id.in_(order_ids), Offer.status.in_(ACTIVE_STATUSES))
            .group_by(Offer.order_id)
        )
        return dict(rows.all())

    async def statuses_for_workshop(self, workshop_id: UUID, order_ids: Sequence[UUID]) -> dict[UUID, str]:
        if not order_ids:
            return {}
        rows = await self._session.execute(
            select(Offer.order_id, Offer.status).where(Offer.workshop_id == workshop_id, Offer.order_id.in_(order_ids))
        )
        return dict(rows.all())

    async def reject_pending(self, order_id: UUID, *, except_id: UUID | None = None) -> None:
        query = update(Offer).where(Offer.order_id == order_id, Offer.status == OfferStatusEnum.PENDING)
        if except_id is not None:
            query = query.where(Offer.id != except_id)
        await self._session.execute(query.values(status=OfferStatusEnum.REJECTED))
