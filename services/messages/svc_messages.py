from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import (
    InvalidStatusError,
    PermissionDeniedError,
    ThreadRequiredError,
    WorkshopRequiredError,
)
from enums.i18n_enum import LanguageEnum
from enums.messages_enum import MessageAuthorEnum
from enums.notifications_enum import NotificationKindEnum
from enums.orders_enum import OrderStatusEnum
from managers.messages.mng_messages import MessageManager
from managers.offers.mng_offers import OfferManager
from managers.orders.mng_orders import OrderManager
from managers.workshops.mng_workshops import WorkshopManager
from models.messages.mdl_message import Message
from models.orders.mdl_order import Order
from models.workshops.mdl_workshop import Workshop
from schemas.auth.sch_auth import CurrentUserSchema
from schemas.messages.sch_message import (
    MessageCreateSchema,
    MessageSchema,
    MessageThreadSchema,
    ThreadFilterSchema,
    ThreadSchema,
)
from schemas.sch_base import PageSchema, language_context
from schemas.workshops.sch_workshop import WorkshopPublicSchema
from services.notifications.svc_notifications import NotificationService
from services.users.svc_users import UserService, user_display_name
from services.workshops.svc_workshops import WorkshopService


@dataclass(frozen=True, slots=True)
class _Thread:
    order: Order
    workshop: Workshop
    viewer_is_client: bool

    @property
    def can_write(self) -> bool:
        # After a workshop is chosen only its thread stays open
        if self.order.status == OrderStatusEnum.CANCELLED:
            return False
        return self.order.status == OrderStatusEnum.PUBLISHED or self.order.workshop_id == self.workshop.id


def _message_schema(message: Message, order: Order, viewer_id: UUID) -> MessageSchema:
    return MessageSchema(
        id=message.id,
        author=MessageAuthorEnum.CLIENT if message.author_id == order.client_id else MessageAuthorEnum.WORKSHOP,
        is_mine=message.author_id == viewer_id,
        body=message.body,
        read_at=message.read_at,
        created_at=message.created_at,
    )


class MessageService:
    def __init__(
        self,
        session: AsyncSession,
        mng_messages: MessageManager,
        mng_orders: OrderManager,
        mng_offers: OfferManager,
        mng_workshops: WorkshopManager,
        svc_workshops: WorkshopService,
        svc_users: UserService,
        svc_notifications: NotificationService,
    ) -> None:
        self._session = session
        self._mng_messages = mng_messages
        self._mng_orders = mng_orders
        self._mng_offers = mng_offers
        self._mng_workshops = mng_workshops
        self._svc_workshops = svc_workshops
        self._svc_users = svc_users
        self._svc_notifications = svc_notifications

    async def list_order_threads(
        self, current: CurrentUserSchema, order_id: UUID, language: LanguageEnum
    ) -> PageSchema[ThreadSchema]:
        order = await self._get_order(order_id)
        if order.client_id == current.id:
            offers = {offer.workshop_id: offer for offer in await self._mng_offers.list_by_order(order.id)}
            last = await self._mng_messages.last_by_workshop(order.id)
            workshop_ids = list(offers.keys() | last.keys())
            workshops = {workshop.id: workshop for workshop in await self._mng_workshops.list_with_city(workshop_ids)}
            threads = [
                _Thread(order, workshops[wid], viewer_is_client=True) for wid in workshop_ids if wid in workshops
            ]
        else:
            thread = await self._resolve(current, order, None)
            offer = await self._mng_offers.get_for_workshop(order.id, thread.workshop.id)
            offers = {offer.workshop_id: offer} if offer else {}
            last = await self._mng_messages.last_by_workshop(order.id)
            threads = [thread]

        unread = await self._mng_messages.unread_by_workshop(order.id, current.id)
        context = language_context(language)
        items = [
            ThreadSchema(
                workshop=WorkshopPublicSchema.model_validate(thread.workshop, context=context),
                offer_status=offers[thread.workshop.id].status if thread.workshop.id in offers else None,
                unread_count=unread.get(thread.workshop.id, 0),
                last_message=(
                    _message_schema(last[thread.workshop.id], order, current.id) if thread.workshop.id in last else None
                ),
                can_write=thread.can_write,
            )
            for thread in threads
        ]
        items.sort(
            key=lambda item: item.last_message.created_at if item.last_message else datetime.min.replace(tzinfo=UTC),
            reverse=True,
        )
        return PageSchema(items=items, total=len(items))

    async def get_order_thread(
        self, current: CurrentUserSchema, order_id: UUID, filters: ThreadFilterSchema, language: LanguageEnum
    ) -> MessageThreadSchema:
        """Returns the thread and marks the incoming messages as read."""
        order = await self._get_order(order_id)
        thread = await self._resolve(current, order, filters.workshop_id)
        now = datetime.now(UTC)
        await self._mng_messages.mark_read(order.id, thread.workshop.id, current.id, now)
        await self._svc_notifications.mark_order_read(current.id, order.id, NotificationKindEnum.MESSAGE_RECEIVED)
        await self._session.commit()
        messages = await self._mng_messages.list_thread(order.id, thread.workshop.id)
        return MessageThreadSchema(
            workshop=WorkshopPublicSchema.model_validate(thread.workshop, context=language_context(language)),
            can_write=thread.can_write,
            messages=[_message_schema(message, order, current.id) for message in messages],
        )

    async def send_order_message(
        self, current: CurrentUserSchema, order_id: UUID, data: MessageCreateSchema
    ) -> MessageSchema:
        order = await self._get_order(order_id)
        thread = await self._resolve(current, order, data.workshop_id)
        if not thread.can_write:
            raise InvalidStatusError("The conversation is closed")
        author = await self._svc_users.sync_user(current)
        message = await self._mng_messages.add(
            Message(order_id=order.id, workshop_id=thread.workshop.id, author_id=current.id, body=data.body)
        )
        if thread.viewer_is_client:
            recipient, actor = thread.workshop.owner_id, user_display_name(author)
        else:
            recipient, actor = order.client_id, thread.workshop.name
        await self._svc_notifications.notify(
            recipient, NotificationKindEnum.MESSAGE_RECEIVED, subject=order.title, order_id=order.id, actor=actor
        )
        await self._session.commit()
        return _message_schema(message, order, current.id)

    async def _get_order(self, order_id: UUID) -> Order:
        order = await self._mng_orders.get_by_id(order_id)
        if order is None:
            raise PermissionDeniedError("Order is not available")
        return order

    async def _resolve(self, current: CurrentUserSchema, order: Order, workshop_id: UUID | None) -> _Thread:
        if order.client_id == current.id:
            if workshop_id is None:
                raise ThreadRequiredError("Pass workshopId to open a conversation")
            workshop = await self._mng_workshops.get_with_city(workshop_id)
            if workshop is None or not await self._takes_part(order, workshop.id):
                raise PermissionDeniedError("The workshop does not take part in this order")
            return _Thread(order, workshop, viewer_is_client=True)

        workshop = await self._svc_workshops.get_approved_or_none(current.id)
        if workshop is None:
            raise WorkshopRequiredError("An approved workshop is required")
        if order.status != OrderStatusEnum.PUBLISHED and not await self._takes_part(order, workshop.id):
            raise PermissionDeniedError("Order is not available")
        return _Thread(order, workshop, viewer_is_client=False)

    async def _takes_part(self, order: Order, workshop_id: UUID) -> bool:
        if order.workshop_id == workshop_id:
            return True
        if await self._mng_offers.get_for_workshop(order.id, workshop_id) is not None:
            return True
        return await self._mng_messages.has_thread(order.id, workshop_id)
