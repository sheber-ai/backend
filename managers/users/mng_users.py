from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import selectinload

from managers.mng_base import BaseManager
from models.users.mdl_user import User


class UserManager(BaseManager[User]):
    model = User

    async def get_with_city(self, user_id: UUID) -> User | None:
        return await self._session.scalar(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.city))
            .execution_options(populate_existing=True)
        )

    async def ensure(self, user_id: UUID, *, email: str | None, first_name: str | None, last_name: str | None) -> User:
        """Create the profile on first sight; concurrent first requests must not fail."""
        await self._session.execute(
            insert(User)
            .values(id=user_id, email=email, first_name=first_name, last_name=last_name)
            .on_conflict_do_nothing(index_elements=[User.id])
        )
        user = await self.get_with_city(user_id)
        if user is None:
            raise LookupError(f"User {user_id} vanished after upsert")
        if email and user.email != email:
            user.email = email
        return user
