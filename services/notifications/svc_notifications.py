from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import NotFoundError
from enums.notifications_enum import NotificationKindEnum
from managers.notifications.mng_notifications import NotificationManager
from managers.workshops.mng_workshops import WorkshopManager
from models.notifications.mdl_notification import Notification
from models.orders.mdl_order import Order
from schemas.auth.sch_auth import CurrentUserSchema
from schemas.notifications.sch_notification import (
    NotificationFilterSchema,
    NotificationSchema,
    NotificationSummarySchema,
)
from schemas.sch_base import PageSchema

# Repeated events of these kinds bump one unread notification instead of piling up
_COALESCED_KINDS = frozenset({NotificationKindEnum.MESSAGE_RECEIVED})


class NotificationService:
    def __init__(
        self, session: AsyncSession, mng_notifications: NotificationManager, mng_workshops: WorkshopManager
    ) -> None:
        self._session = session
        self._mng_notifications = mng_notifications
        self._mng_workshops = mng_workshops

    async def notify(
        self,
        user_id: UUID,
        kind: NotificationKindEnum,
        *,
        subject: str,
        order_id: UUID | None = None,
        actor: str | None = None,
    ) -> None:
        """Adds a notification to the caller's transaction. Does not commit."""
        if kind in _COALESCED_KINDS:
            existing = await self._mng_notifications.find_unread(user_id, kind, order_id)
            if existing is not None:
                existing.created_at = datetime.now(UTC)
                existing.actor = actor
                existing.subject = subject
                return
        await self._mng_notifications.add(
            Notification(user_id=user_id, kind=kind, order_id=order_id, subject=subject, actor=actor)
        )

    async def notify_workshops(
        self,
        workshop_ids: Sequence[UUID],
        kind: NotificationKindEnum,
        *,
        subject: str,
        order_id: UUID | None = None,
        actor: str | None = None,
    ) -> None:
        for owner_id in await self._mng_workshops.owner_ids(workshop_ids):
            await self.notify(owner_id, kind, subject=subject, order_id=order_id, actor=actor)

    async def notify_new_order(self, order: Order) -> None:
        """Tells workshops that serve the order's city and make its furniture type. Does not commit."""
        owner_ids = await self._mng_workshops.owner_ids_for_order(
            city_id=order.city_id, furniture_type=order.furniture_type, exclude_owner_id=order.client_id
        )
        for owner_id in owner_ids:
            await self.notify(owner_id, NotificationKindEnum.NEW_ORDER, subject=order.title, order_id=order.id)

    async def mark_order_read(self, user_id: UUID, order_id: UUID, kind: NotificationKindEnum) -> None:
        """Does not commit."""
        await self._mng_notifications.mark_read(user_id, datetime.now(UTC), order_id=order_id, kind=kind)

    async def list_notifications(
        self, current: CurrentUserSchema, filters: NotificationFilterSchema
    ) -> PageSchema[NotificationSchema]:
        items, total = await self._mng_notifications.list_for_user(
            current.id, unread_only=filters.unread_only, offset=filters.offset, limit=filters.limit
        )
        return PageSchema(items=[NotificationSchema.model_validate(item) for item in items], total=total)

    async def get_notification_summary(self, current: CurrentUserSchema) -> NotificationSummarySchema:
        return NotificationSummarySchema(unread=await self._mng_notifications.count_unread(current.id))

    async def read_notification(self, current: CurrentUserSchema, notification_id: UUID) -> NotificationSchema:
        notification = await self._mng_notifications.get_by_id(notification_id)
        if notification is None or notification.user_id != current.id:
            raise NotFoundError(f"Notification {notification_id} not found")
        if notification.read_at is None:
            notification.read_at = datetime.now(UTC)
            await self._session.commit()
        return NotificationSchema.model_validate(notification)

    async def read_all_notifications(self, current: CurrentUserSchema) -> NotificationSummarySchema:
        await self._mng_notifications.mark_read(current.id, datetime.now(UTC))
        await self._session.commit()
        return NotificationSummarySchema(unread=0)
