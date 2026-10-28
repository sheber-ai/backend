from typing import Annotated
from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Query, status

from rest_api.dependencies import ContractorUser, CurrentUser, Language
from schemas.offers.sch_offer import OfferCreateSchema, OfferSchema, OfferWithWorkshopSchema
from schemas.orders.sch_order import (
    MyOrdersFilterSchema,
    MyOrdersPageSchema,
    OrderCreateSchema,
    OrderDetailSchema,
    OrderFeedFilterSchema,
    OrderFeedItemSchema,
)
from schemas.sch_base import PageSchema
from services.offers.svc_offers import OfferService
from services.orders.svc_orders import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", status_code=status.HTTP_201_CREATED)
@inject
async def create_order(
    body: OrderCreateSchema, user: CurrentUser, language: Language, svc_orders: Injected[OrderService]
) -> OrderDetailSchema:
    return await svc_orders.create_order(user, body, language)


@router.get("/mine")
@inject
async def list_my_orders(
    filters: Annotated[MyOrdersFilterSchema, Query()],
    user: CurrentUser,
    language: Language,
    svc_orders: Injected[OrderService],
) -> MyOrdersPageSchema:
    return await svc_orders.list_my_orders(user, filters, language)


@router.get("/feed")
@inject
async def list_order_feed(
    filters: Annotated[OrderFeedFilterSchema, Query()],
    user: ContractorUser,
    language: Language,
    svc_orders: Injected[OrderService],
) -> PageSchema[OrderFeedItemSchema]:
    return await svc_orders.list_order_feed(user, filters, language)


@router.get("/{order_id}")
@inject
async def get_order(
    order_id: UUID, user: CurrentUser, language: Language, svc_orders: Injected[OrderService]
) -> OrderDetailSchema:
    return await svc_orders.get_order(user, order_id, language)


@router.post("/{order_id}/cancel")
@inject
async def cancel_order(
    order_id: UUID, user: CurrentUser, language: Language, svc_orders: Injected[OrderService]
) -> OrderDetailSchema:
    return await svc_orders.cancel_order(user, order_id, language)


@router.post("/{order_id}/start")
@inject
async def start_order(
    order_id: UUID, user: ContractorUser, language: Language, svc_orders: Injected[OrderService]
) -> OrderDetailSchema:
    return await svc_orders.start_order(user, order_id, language)


@router.post("/{order_id}/complete")
@inject
async def complete_order(
    order_id: UUID, user: CurrentUser, language: Language, svc_orders: Injected[OrderService]
) -> OrderDetailSchema:
    return await svc_orders.complete_order(user, order_id, language)


@router.get("/{order_id}/offers")
@inject
async def list_order_offers(
    order_id: UUID, user: CurrentUser, language: Language, svc_offers: Injected[OfferService]
) -> PageSchema[OfferWithWorkshopSchema]:
    return await svc_offers.list_order_offers(user, order_id, language)


@router.post("/{order_id}/offers", status_code=status.HTTP_201_CREATED)
@inject
async def create_offer(
    order_id: UUID, body: OfferCreateSchema, user: ContractorUser, svc_offers: Injected[OfferService]
) -> OfferSchema:
    return await svc_offers.create_offer(user, order_id, body)
