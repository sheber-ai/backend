from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select

from managers.mng_base import BaseManager
from models.designs.mdl_design import Design


class DesignManager(BaseManager[Design]):
    model = Design

    async def list_by_owner(self, owner_id: UUID, *, offset: int, limit: int) -> tuple[Sequence[Design], int]:
        condition = Design.owner_id == owner_id
        total = await self._session.scalar(select(func.count()).where(condition)) or 0
        items = await self._session.scalars(
            select(Design).where(condition).order_by(Design.updated_at.desc()).offset(offset).limit(limit)
        )
        return items.all(), total
