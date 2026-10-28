from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.orm import selectinload

from common.exceptions import NotFoundError
from enums.offers_enum import OfferStatusEnum
from enums.orders_enum import OrderGroupEnum, OrderStatusEnum
from managers.mng_base import BaseManager
from models.offers.mdl_offer import Offer
from models.orders.mdl_order import Order
from models.workshops.mdl_workshop import Workshop

ACTIVE_ORDER_STATUSES = (OrderStatusEnum.PUBLISHED, OrderStatusEnum.ASSIGNED, OrderStatusEnum.IN_PROGRESS)
GROUP_STATUSES: dict[OrderGroupEnum, tuple[OrderStatusEnum, ...]] = {
    OrderGroupEnum.ACTIVE: ACTIVE_ORDER_STATUSES,
    OrderGroupEnum.COMPLETED: (OrderStatusEnum.COMPLETED,),
    OrderGroupEnum.CANCELLED: (OrderStatusEnum.CANCELLED,),
}


class OrderManager(BaseManager[Order]):
    model = Order

    async def get_with_relations(self, order_id: UUID) -> Order | None:
        return await self._session.scalar(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.client),
                selectinload(Order.city),
                selectinload(Order.workshop).selectinload(Workshop.city),
            )
            .execution_options(populate_existing=True)
        )

    async def get_for_update(self, order_id: UUID) -> Order:
        order = await self._session.scalar(
            select(Order).where(Order.id == order_id).with_for_update().execution_options(populate_existing=True)
        )
        if order is None:
            raise NotFoundError(f"Order {order_id} not found")
        return order

    async def list_by_client(
        self, client_id: UUID, *, group: OrderGroupEnum | None, offset: int, limit: int
    ) -> tuple[Sequence[Order], int]:
        condition = Order.client_id == client_id
        if group is not None:
            condition = condition & Order.status.in_(GROUP_STATUSES[group])
        total = await self._session.scalar(select(func.count()).select_from(Order).where(condition)) or 0
        items = await self._session.scalars(
            select(Order)
            .where(condition)
            .options(selectinload(Order.city))
            # id breaks ties so pages never repeat or skip an order
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return items.all(), total

    async def count_groups_by_client(self, client_id: UUID) -> dict[OrderGroupEnum, int]:
        rows = await self._session.execute(
            select(Order.status, func.count()).where(Order.client_id == client_id).group_by(Order.status)
        )
        by_status: dict[str, int] = dict(rows.all())
        return {
            group: sum(by_status.get(status, 0) for status in statuses) for group, statuses in GROUP_STATUSES.items()
        }

    async def list_published(
        self,
        *,
        exclude_client_id: UUID,
        city_id: UUID | None,
        city_ids: Sequence[UUID] | None = None,
        furniture_type: str | None,
        exclude_offered_by: UUID | None = None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Order], int]:
        conditions = [Order.status == OrderStatusEnum.PUBLISHED, Order.client_id != exclude_client_id]
        if exclude_offered_by is not None:
            # A withdrawn offer does not count: the workshop may respond again
            conditions.append(
                ~exists().where(
                    Offer.order_id == Order.id,
                    Offer.workshop_id == exclude_offered_by,
                    Offer.status != OfferStatusEnum.WITHDRAWN,
                )
            )
        if city_id is not None:
            conditions.append(Order.city_id == city_id)
        if city_ids is not None:
            conditions.append(Order.city_id.in_(city_ids))
        if furniture_type is not None:
            conditions.append(Order.furniture_type == furniture_type)
        total = await self._session.scalar(select(func.count()).where(*conditions)) or 0
        items = await self._session.scalars(
            select(Order)
            .where(*conditions)
            .options(selectinload(Order.city))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return items.all(), total

    async def count_completed_by_workshop(self, workshop_id: UUID) -> int:
        query = select(func.count()).where(Order.workshop_id == workshop_id, Order.status == OrderStatusEnum.COMPLETED)
        return await self._session.scalar(query) or 0

    async def active_by_designs(self, design_ids: Sequence[UUID]) -> dict[UUID, Order]:
        """Latest unfinished order of each design."""
        if not design_ids:
            return {}
        items = await self._session.scalars(
            select(Order)
            .where(Order.design_id.in_(design_ids), Order.status.in_(ACTIVE_ORDER_STATUSES))
            .order_by(Order.created_at)
        )
        return {order.design_id: order for order in items if order.design_id is not None}
