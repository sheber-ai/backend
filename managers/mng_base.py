from collections.abc import Sequence
from typing import Any, ClassVar
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import NotFoundError
from models.mdl_base import Base


class BaseManager[ModelT: Base]:
    """DB queries for one model. Never commits."""

    model: ClassVar[type[Any]]

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, id_: UUID) -> ModelT | None:
        return await self._session.get(self.model, id_)

    async def get_by_id_or_raise(self, id_: UUID) -> ModelT:
        obj = await self.get_by_id(id_)
        if obj is None:
            raise NotFoundError(f"{self.model.__name__} {id_} not found")
        return obj

    async def list(self, *, offset: int = 0, limit: int = 50) -> Sequence[ModelT]:
        query = select(self.model).offset(offset).limit(limit)
        return (await self._session.scalars(query)).all()

    async def count(self) -> int:
        query = select(func.count()).select_from(self.model)
        return (await self._session.scalar(query)) or 0

    async def add(self, obj: ModelT) -> ModelT:
        self._session.add(obj)
        await self._session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self._session.delete(obj)
        await self._session.flush()
