from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select

from managers.mng_base import BaseManager
from models.imports.mdl_import_request import ImportRequest


class ImportRequestManager(BaseManager[ImportRequest]):
    model = ImportRequest

    async def lock_user(self, user_id: UUID) -> None:
        """Serializes rate checks of one user until the transaction ends, across API processes."""
        await self._session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(str(user_id), 0))))

    async def purge_before(self, user_id: UUID, moment: datetime) -> None:
        await self._session.execute(
            delete(ImportRequest).where(ImportRequest.user_id == user_id, ImportRequest.created_at < moment)
        )

    async def window(self, user_id: UUID, since: datetime) -> tuple[int, datetime | None]:
        """Requests since the moment and the oldest of them."""
        row = (
            await self._session.execute(
                select(func.count(), func.min(ImportRequest.created_at)).where(
                    ImportRequest.user_id == user_id, ImportRequest.created_at >= since
                )
            )
        ).one()
        return row[0], row[1]
