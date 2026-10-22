from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import InvalidStatusError, PermissionDeniedError, ProfileIncompleteError
from enums.auth_enum import UserRoleEnum
from enums.i18n_enum import LanguageEnum
from enums.orders_enum import OrderStatusEnum
from managers.offers.mng_offers import OfferManager
from managers.orders.mng_orders import OrderManager
from models.orders.mdl_order import Order
from models.workshops.mdl_workshop import Workshop
from schemas.auth.sch_auth import CurrentUserSchema
from schemas.offers.sch_offer import OfferSchema
from schemas.orders.sch_order import (
    OrderCreateSchema,
    OrderDetailSchema,
    OrderFeedFilterSchema,
    OrderFeedItemSchema,
    OrderSchema,
)
from schemas.sch_base import PageSchema, PaginationSchema, language_context
from schemas.users.sch_user import ContactSchema
from services.cities.svc_cities import CityService
from services.designs.svc_designs import DesignService
from services.users.svc_users import UserService, user_contact
from services.workshops.svc_workshops import WorkshopService

_ORDER_FIELDS = tuple(name for name in OrderSchema.model_fields if name != "offers_count")


def order_fields(order: Order) -> dict[str, Any]:
    return {name: getattr(order, name) for name in _ORDER_FIELDS}


class OrderService:
    def __init__(
        self,
        session: AsyncSession,
        mng_orders: OrderManager,
        mng_offers: OfferManager,
        svc_users: UserService,
        svc_designs: DesignService,
        svc_workshops: WorkshopService,
        svc_cities: CityService,
    ) -> None:
        self._session = session
        self._mng_orders = mng_orders
        self._mng_offers = mng_offers
        self._svc_users = svc_users
        self._svc_designs = svc_designs
        self._svc_workshops = svc_workshops
        self._svc_cities = svc_cities

    async def create_order(
        self, current: CurrentUserSchema, data: OrderCreateSchema, language: LanguageEnum
    ) -> OrderDetailSchema:
        await self._svc_cities.require_active(data.city_id)
        user = await self._svc_users.sync_user(current)
        if not user.phone:
            raise ProfileIncompleteError("Fill in the phone number before publishing an order")
        design = await self._svc_designs.get_own(current, data.design_id)
        order = await self._mng_orders.add(
            Order(
                client_id=current.id,
                design_id=design.id,
                title=design.title,
                furniture_type=design.furniture_type,
                document=design.document,
                source_url=design.source_url,
                **data.model_dump(by_alias=False, exclude={"design_id"}),
            )
        )
        await self._session.commit()
        return await self.get_order(current, order.id, language)

    async def list_my_orders(
        self, current: CurrentUserSchema, pagination: PaginationSchema, language: LanguageEnum
    ) -> PageSchema[OrderSchema]:
        items, total = await self._mng_orders.list_by_client(
            current.id, offset=pagination.offset, limit=pagination.limit
        )
        counts = await self._mng_offers.count_active_by_orders([order.id for order in items])
        return PageSchema(
            items=[
                OrderSchema.model_validate(
                    {**order_fields(order), "offers_count": counts.get(order.id, 0)},
                    context=language_context(language),
                )
                for order in items
            ],
            total=total,
        )

    async def list_order_feed(
        self, current: CurrentUserSchema, filters: OrderFeedFilterSchema, language: LanguageEnum
    ) -> PageSchema[OrderFeedItemSchema]:
        workshop = await self._svc_workshops.require_approved(current)
        items, total = await self._mng_orders.list_published(
            exclude_client_id=current.id,
            city_id=filters.city_id,
            furniture_type=filters.furniture_type,
            offset=filters.offset,
            limit=filters.limit,
        )
        ids = [order.id for order in items]
        counts = await self._mng_offers.count_active_by_orders(ids)
        statuses = await self._mng_offers.statuses_for_workshop(workshop.id, ids)
        return PageSchema(
            items=[
                OrderFeedItemSchema.model_validate(
                    {
                        **order_fields(order),
                        "offers_count": counts.get(order.id, 0),
                        "my_offer_status": statuses.get(order.id),
                    },
                    context=language_context(language),
                )
                for order in items
            ],
            total=total,
        )

    async def get_order(self, current: CurrentUserSchema, order_id: UUID, language: LanguageEnum) -> OrderDetailSchema:
        order = await self._get_with_relations(order_id)
        is_owner = order.client_id == current.id
        workshop = None if is_owner else await self._svc_workshops.get_approved_or_none(current.id)
        my_offer = await self._mng_offers.get_for_workshop(order.id, workshop.id) if workshop else None

        if not (is_owner or current.has_role(UserRoleEnum.ADMIN) or self._workshop_can_see(order, workshop, my_offer)):
            raise PermissionDeniedError("Order is not available")

        contact: ContactSchema | None = None
        if is_owner and order.workshop is not None:
            contact = await self._workshop_contact(order.workshop)
        elif workshop is not None and order.workshop_id == workshop.id:
            contact = user_contact(order.client)

        counts = await self._mng_offers.count_active_by_orders([order.id])
        return OrderDetailSchema.model_validate(
            {
                **order_fields(order),
                "offers_count": counts.get(order.id, 0),
                "design_id": order.design_id if is_owner else None,
                "is_owner": is_owner,
                "workshop": order.workshop,
                "my_offer": OfferSchema.model_validate(my_offer) if my_offer else None,
                "contact": contact,
            },
            context=language_context(language),
        )

    async def cancel_order(
        self, current: CurrentUserSchema, order_id: UUID, language: LanguageEnum
    ) -> OrderDetailSchema:
        order = await self._get_owned(current, order_id)
        self._require_status(order, OrderStatusEnum.PUBLISHED, OrderStatusEnum.ASSIGNED)
        order.status = OrderStatusEnum.CANCELLED
        await self._mng_offers.reject_pending(order.id)
        await self._session.commit()
        return await self.get_order(current, order_id, language)

    async def start_order(
        self, current: CurrentUserSchema, order_id: UUID, language: LanguageEnum
    ) -> OrderDetailSchema:
        workshop = await self._svc_workshops.require_approved(current)
        order = await self._mng_orders.get_by_id_or_raise(order_id)
        if order.workshop_id != workshop.id:
            raise PermissionDeniedError("Order is assigned to another workshop")
        self._require_status(order, OrderStatusEnum.ASSIGNED)
        order.status = OrderStatusEnum.IN_PROGRESS
        await self._session.commit()
        return await self.get_order(current, order_id, language)

    async def complete_order(
        self, current: CurrentUserSchema, order_id: UUID, language: LanguageEnum
    ) -> OrderDetailSchema:
        order = await self._get_owned(current, order_id)
        self._require_status(order, OrderStatusEnum.ASSIGNED, OrderStatusEnum.IN_PROGRESS)
        order.status = OrderStatusEnum.COMPLETED
        await self._session.commit()
        return await self.get_order(current, order_id, language)

    async def _get_with_relations(self, order_id: UUID) -> Order:
        order = await self._mng_orders.get_with_relations(order_id)
        if order is None:
            raise PermissionDeniedError("Order is not available")
        return order

    async def _get_owned(self, current: CurrentUserSchema, order_id: UUID) -> Order:
        order = await self._mng_orders.get_by_id_or_raise(order_id)
        if order.client_id != current.id:
            raise PermissionDeniedError("Not your order")
        return order

    async def _workshop_contact(self, workshop: Workshop) -> ContactSchema:
        owner = await self._svc_users.get_user(workshop.owner_id)
        return ContactSchema(name=workshop.name, phone=workshop.phone, email=owner.email if owner else None)

    @staticmethod
    def _workshop_can_see(order: Order, workshop: Workshop | None, my_offer: object | None) -> bool:
        if workshop is None:
            return False
        return order.status == OrderStatusEnum.PUBLISHED or order.workshop_id == workshop.id or my_offer is not None

    @staticmethod
    def _require_status(order: Order, *allowed: OrderStatusEnum) -> None:
        if order.status not in allowed:
            raise InvalidStatusError(f"Order is {order.status}, expected one of {', '.join(allowed)}")
