from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import distinct_on

from managers.mng_base import BaseManager
from models.messages.mdl_message import Message

THREAD_LIMIT = 500


class MessageManager(BaseManager[Message]):
    model = Message

    async def list_thread(self, order_id: UUID, workshop_id: UUID) -> Sequence[Message]:
        """The latest THREAD_LIMIT messages, oldest first."""
        latest = (
            select(Message)
            .where(Message.order_id == order_id, Message.workshop_id == workshop_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(THREAD_LIMIT)
        )
        items = (await self._session.scalars(latest)).all()
        return list(reversed(items))

    async def has_thread(self, order_id: UUID, workshop_id: UUID) -> bool:
        query = select(Message.id).where(Message.order_id == order_id, Message.workshop_id == workshop_id).limit(1)
        return await self._session.scalar(query) is not None

    async def unread_by_workshop(self, order_id: UUID, reader_id: UUID) -> dict[UUID, int]:
        rows = await self._session.execute(
            select(Message.workshop_id, func.count())
            .where(Message.order_id == order_id, Message.author_id != reader_id, Message.read_at.is_(None))
            .group_by(Message.workshop_id)
        )
        return dict(rows.all())

    async def last_by_workshop(self, order_id: UUID) -> dict[UUID, Message]:
        items = await self._session.scalars(
            select(Message)
            .where(Message.order_id == order_id)
            .ext(distinct_on(Message.workshop_id))
            .order_by(Message.workshop_id, Message.created_at.desc(), Message.id.desc())
        )
        return {message.workshop_id: message for message in items}

    async def mark_read(self, order_id: UUID, workshop_id: UUID, reader_id: UUID, now: datetime) -> None:
        await self._session.execute(
            update(Message)
            .where(
                Message.order_id == order_id,
                Message.workshop_id == workshop_id,
                Message.author_id != reader_id,
                Message.read_at.is_(None),
            )
            .values(read_at=now)
        )
