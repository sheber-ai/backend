from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update

from managers.mng_base import BaseManager
from models.notifications.mdl_notification import Notification


class NotificationManager(BaseManager[Notification]):
    model = Notification

    async def list_for_user(
        self, user_id: UUID, *, unread_only: bool, offset: int, limit: int
    ) -> tuple[Sequence[Notification], int]:
        conditions = [Notification.user_id == user_id]
        if unread_only:
            conditions.append(Notification.read_at.is_(None))
        total = await self._session.scalar(select(func.count()).select_from(Notification).where(*conditions)) or 0
        items = await self._session.scalars(
            select(Notification)
            .where(*conditions)
            .order_by(Notification.created_at.desc(), Notification.id)
            .offset(offset)
            .limit(limit)
        )
        return items.all(), total

    async def count_unread(self, user_id: UUID) -> int:
        query = select(func.count()).where(Notification.user_id == user_id, Notification.read_at.is_(None))
        return await self._session.scalar(query) or 0

    async def find_unread(self, user_id: UUID, kind: str, order_id: UUID | None) -> Notification | None:
        return await self._session.scalar(
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.kind == kind,
                Notification.order_id == order_id,
                Notification.read_at.is_(None),
            )
            .limit(1)
        )

    async def mark_read(
        self,
        user_id: UUID,
        now: datetime,
        *,
        ids: Sequence[UUID] | None = None,
        order_id: UUID | None = None,
        kind: str | None = None,
    ) -> None:
        query = update(Notification).where(Notification.user_id == user_id, Notification.read_at.is_(None))
        if ids is not None:
            query = query.where(Notification.id.in_(ids))
        if order_id is not None:
            query = query.where(Notification.order_id == order_id)
        if kind is not None:
            query = query.where(Notification.kind == kind)
        await self._session.execute(query.values(read_at=now))
