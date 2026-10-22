from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from common.exceptions import NotFoundError
from enums.orders_enum import OrderStatusEnum
from managers.mng_base import BaseManager
from models.orders.mdl_order import Order
from models.workshops.mdl_workshop import Workshop


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

    async def list_by_client(self, client_id: UUID, *, offset: int, limit: int) -> tuple[Sequence[Order], int]:
        condition = Order.client_id == client_id
        total = await self._session.scalar(select(func.count()).where(condition)) or 0
        items = await self._session.scalars(
            select(Order)
            .where(condition)
            .options(selectinload(Order.city))
            .order_by(Order.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return items.all(), total

    async def list_published(
        self,
        *,
        exclude_client_id: UUID,
        city_id: UUID | None,
        furniture_type: str | None,
        offset: int,
        limit: int,
    ) -> tuple[Sequence[Order], int]:
        conditions = [Order.status == OrderStatusEnum.PUBLISHED, Order.client_id != exclude_client_id]
        if city_id is not None:
            conditions.append(Order.city_id == city_id)
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
