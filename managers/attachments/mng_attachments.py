from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select

from managers.mng_base import BaseManager
from models.attachments.mdl_attachment import Attachment


class AttachmentManager(BaseManager[Attachment]):
    model = Attachment

    async def list_for(
        self,
        *,
        workshop_id: UUID | None = None,
        design_id: UUID | None = None,
        order_id: UUID | None = None,
        purpose: str | None = None,
    ) -> Sequence[Attachment]:
        conditions = [
            Attachment.workshop_id == workshop_id if workshop_id else Attachment.workshop_id.is_(None),
            Attachment.design_id == design_id if design_id else Attachment.design_id.is_(None),
            Attachment.order_id == order_id if order_id else Attachment.order_id.is_(None),
        ]
        if purpose is not None:
            conditions.append(Attachment.purpose == purpose)
        items = await self._session.scalars(
            select(Attachment).where(*conditions).order_by(Attachment.position, Attachment.created_at)
        )
        return items.all()

    async def count_by_purpose(
        self, purpose: str, *, workshop_id: UUID | None, design_id: UUID | None, order_id: UUID | None
    ) -> int:
        return len(
            await self.list_for(workshop_id=workshop_id, design_id=design_id, order_id=order_id, purpose=purpose)
        )

    async def key_in_use(self, storage_key: str) -> bool:
        query = select(func.count()).where(Attachment.storage_key == storage_key)
        return bool(await self._session.scalar(query))
