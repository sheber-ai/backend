from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import InvalidStatusError, OfferExistsError, PermissionDeniedError
from enums.i18n_enum import LanguageEnum
from enums.notifications_enum import NotificationKindEnum
from enums.offers_enum import OfferStatusEnum, OfferTabEnum
from enums.orders_enum import OrderStatusEnum
from managers.offers.mng_offers import OfferManager
from managers.orders.mng_orders import OrderManager
from models.offers.mdl_offer import Offer
from schemas.auth.sch_auth import CurrentUserSchema
from schemas.offers.sch_offer import (
    MyOfferSchema,
    MyOffersFilterSchema,
    MyOffersPageSchema,
    OfferCreateSchema,
    OfferSchema,
    OfferTabCountsSchema,
    OfferWithWorkshopSchema,
)
from schemas.sch_base import PageSchema, language_context
from services.notifications.svc_notifications import NotificationService
from services.workshops.svc_workshops import WorkshopService


class OfferService:
    def __init__(
        self,
        session: AsyncSession,
        mng_offers: OfferManager,
        mng_orders: OrderManager,
        svc_workshops: WorkshopService,
        svc_notifications: NotificationService,
    ) -> None:
        self._session = session
        self._mng_offers = mng_offers
        self._mng_orders = mng_orders
        self._svc_workshops = svc_workshops
        self._svc_notifications = svc_notifications

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
        await self._svc_notifications.notify(
            order.client_id,
            NotificationKindEnum.OFFER_RECEIVED,
            subject=order.title,
            order_id=order.id,
            actor=workshop.name,
        )
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
        self, current: CurrentUserSchema, filters: MyOffersFilterSchema, language: LanguageEnum
    ) -> MyOffersPageSchema:
        workshop = await self._svc_workshops.require_approved(current)
        offers, total = await self._mng_offers.list_by_workshop(
            workshop.id, tab=filters.tab, offset=filters.offset, limit=filters.limit
        )
        counts = await self._mng_offers.count_tabs_by_workshop(workshop.id)
        items = [MyOfferSchema.model_validate(offer, context=language_context(language)) for offer in offers]
        return MyOffersPageSchema(
            items=items,
            total=total,
            counts=OfferTabCountsSchema(active=counts[OfferTabEnum.ACTIVE], archive=counts[OfferTabEnum.ARCHIVE]),
        )

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
        rejected = await self._mng_offers.reject_pending(order.id, except_id=offer.id)
        await self._svc_notifications.notify_workshops(
            [offer.workshop_id], NotificationKindEnum.OFFER_ACCEPTED, subject=order.title, order_id=order.id
        )
        await self._svc_notifications.notify_workshops(
            rejected, NotificationKindEnum.OFFER_REJECTED, subject=order.title, order_id=order.id
        )
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
