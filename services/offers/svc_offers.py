from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import InvalidStatusError, OfferExistsError, PermissionDeniedError
from enums.i18n_enum import LanguageEnum
from enums.offers_enum import OfferStatusEnum
from enums.orders_enum import OrderStatusEnum
from managers.offers.mng_offers import OfferManager
from managers.orders.mng_orders import OrderManager
from models.offers.mdl_offer import Offer
from schemas.auth.sch_auth import CurrentUserSchema
from schemas.offers.sch_offer import (
    MyOfferSchema,
    OfferCreateSchema,
    OfferSchema,
    OfferWithWorkshopSchema,
)
from schemas.sch_base import PageSchema, PaginationSchema, language_context
from services.workshops.svc_workshops import WorkshopService


class OfferService:
    def __init__(
        self,
        session: AsyncSession,
        mng_offers: OfferManager,
        mng_orders: OrderManager,
        svc_workshops: WorkshopService,
    ) -> None:
        self._session = session
        self._mng_offers = mng_offers
        self._mng_orders = mng_orders
        self._svc_workshops = svc_workshops

    async def create_offer(self, current: CurrentUserSchema, order_id: UUID, data: OfferCreateSchema) -> OfferSchema:
        workshop = await self._svc_workshops.require_approved(current)
        order = await self._mng_orders.get_by_id_or_raise(order_id)
        if order.client_id == current.id:
            raise PermissionDeniedError("Cannot respond to your own order")
        if order.status != OrderStatusEnum.PUBLISHED:
            raise InvalidStatusError("Order is not accepting offers")

        offer = await self._mng_offers.get_for_workshop(order.id, workshop.id)
        if offer is None:
            offer = await self._mng_offers.add(
                Offer(order_id=order.id, workshop_id=workshop.id, **data.model_dump(by_alias=False))
            )
        elif offer.status == OfferStatusEnum.WITHDRAWN:
            for field, value in data.model_dump(by_alias=False).items():
                setattr(offer, field, value)
            offer.status = OfferStatusEnum.PENDING
        else:
            raise OfferExistsError("The workshop has already responded to this order")
        await self._session.commit()
        return OfferSchema.model_validate(offer)

    async def update_offer(self, current: CurrentUserSchema, offer_id: UUID, data: OfferCreateSchema) -> OfferSchema:
        offer = await self._get_own(current, offer_id)
        self._require_pending(offer)
        for field, value in data.model_dump(by_alias=False).items():
            setattr(offer, field, value)
        await self._session.commit()
        return OfferSchema.model_validate(offer)

    async def withdraw_offer(self, current: CurrentUserSchema, offer_id: UUID) -> OfferSchema:
        offer = await self._get_own(current, offer_id)
        self._require_pending(offer)
        offer.status = OfferStatusEnum.WITHDRAWN
        await self._session.commit()
        return OfferSchema.model_validate(offer)

    async def list_order_offers(
        self, current: CurrentUserSchema, order_id: UUID, language: LanguageEnum
    ) -> PageSchema[OfferWithWorkshopSchema]:
        order = await self._mng_orders.get_by_id_or_raise(order_id)
        if order.client_id != current.id:
            raise PermissionDeniedError("Not your order")
        offers = await self._mng_offers.list_by_order(order.id)
        items = [OfferWithWorkshopSchema.model_validate(offer, context=language_context(language)) for offer in offers]
        return PageSchema(items=items, total=len(items))

    async def list_my_offers(
        self, current: CurrentUserSchema, pagination: PaginationSchema, language: LanguageEnum
    ) -> PageSchema[MyOfferSchema]:
        workshop = await self._svc_workshops.require_approved(current)
        offers, total = await self._mng_offers.list_by_workshop(
            workshop.id, offset=pagination.offset, limit=pagination.limit
        )
        items = [MyOfferSchema.model_validate(offer, context=language_context(language)) for offer in offers]
        return PageSchema(items=items, total=total)

    async def accept_offer(self, current: CurrentUserSchema, offer_id: UUID) -> OfferSchema:
        offer = await self._mng_offers.get_with_order(offer_id)
        if offer is None or offer.order.client_id != current.id:
            raise PermissionDeniedError("Not your order")
        # Row lock: two accepts racing on one order must not both win
        order = await self._mng_orders.get_for_update(offer.order_id)
        if order.status != OrderStatusEnum.PUBLISHED:
            raise InvalidStatusError("Order already has a workshop")
        self._require_pending(offer)

        offer.status = OfferStatusEnum.ACCEPTED
        order.status = OrderStatusEnum.ASSIGNED
        order.workshop_id = offer.workshop_id
        await self._mng_offers.reject_pending(order.id, except_id=offer.id)
        await self._session.commit()
        return OfferSchema.model_validate(offer)

    async def _get_own(self, current: CurrentUserSchema, offer_id: UUID) -> Offer:
        workshop = await self._svc_workshops.require_approved(current)
        offer = await self._mng_offers.get_by_id_or_raise(offer_id)
        if offer.workshop_id != workshop.id:
            raise PermissionDeniedError("Not your offer")
        return offer

    @staticmethod
    def _require_pending(offer: Offer) -> None:
        if offer.status != OfferStatusEnum.PENDING:
            raise InvalidStatusError(f"Offer is {offer.status}")
