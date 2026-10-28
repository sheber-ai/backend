from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import ColumnElement, and_, func, or_, select, update
from sqlalchemy.orm import selectinload

from enums.offers_enum import OfferStatusEnum, OfferTabEnum
from enums.orders_enum import OrderStatusEnum
from managers.mng_base import BaseManager
from models.offers.mdl_offer import Offer
from models.orders.mdl_order import Order
from models.workshops.mdl_workshop import Workshop

ACTIVE_STATUSES = (OfferStatusEnum.PENDING, OfferStatusEnum.ACCEPTED)

# Same rule as offerTab() on the frontend: waiting for the client's choice, or chosen and not finished yet
ACTIVE_TAB: ColumnElement[bool] = or_(
    and_(Offer.status == OfferStatusEnum.PENDING, Order.status == OrderStatusEnum.PUBLISHED),
    and_(
        Offer.status == OfferStatusEnum.ACCEPTED,
        Order.status.in_((OrderStatusEnum.ASSIGNED, OrderStatusEnum.IN_PROGRESS)),
    ),
)


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

    async def list_by_workshop(
        self, workshop_id: UUID, *, tab: OfferTabEnum | None, offset: int, limit: int
    ) -> tuple[Sequence[Offer], int]:
        condition: ColumnElement[bool] = Offer.workshop_id == workshop_id
        if tab is OfferTabEnum.ACTIVE:
            condition = and_(condition, ACTIVE_TAB)
        elif tab is OfferTabEnum.ARCHIVE:
            condition = and_(condition, ~ACTIVE_TAB)
        total = (
            await self._session.scalar(
                select(func.count()).select_from(Offer).join(Order, Offer.order_id == Order.id).where(condition)
            )
            or 0
        )
        items = await self._session.scalars(
            select(Offer)
            .join(Order, Offer.order_id == Order.id)
            .where(condition)
            .options(selectinload(Offer.order).selectinload(Order.city))
            # id breaks ties so pages never repeat or skip an offer
            .order_by(Offer.updated_at.desc(), Offer.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return items.all(), total

    async def count_tabs_by_workshop(self, workshop_id: UUID) -> dict[OfferTabEnum, int]:
        row = (
            await self._session.execute(
                select(func.count().filter(ACTIVE_TAB), func.count())
                .select_from(Offer)
                .join(Order, Offer.order_id == Order.id)
                .where(Offer.workshop_id == workshop_id)
            )
        ).one()
        active, total = row
        return {OfferTabEnum.ACTIVE: active, OfferTabEnum.ARCHIVE: total - active}

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

    async def reject_pending(self, order_id: UUID, *, except_id: UUID | None = None) -> list[UUID]:
        """Rejects pending offers and returns their workshop ids."""
        query = update(Offer).where(Offer.order_id == order_id, Offer.status == OfferStatusEnum.PENDING)
        if except_id is not None:
            query = query.where(Offer.id != except_id)
        rows = await self._session.scalars(
            query.values(status=OfferStatusEnum.REJECTED).returning(Offer.workshop_id),
        )
        return list(rows.all())
