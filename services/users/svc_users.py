from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from enums.i18n_enum import LanguageEnum
from managers.users.mng_users import UserManager
from managers.workshops.mng_workshops import WorkshopManager
from models.users.mdl_user import User
from schemas.auth.sch_auth import CurrentUserSchema
from schemas.sch_base import language_context
from schemas.users.sch_user import ContactSchema, UserSchema, UserUpdateSchema
from services.cities.svc_cities import CityService


def user_display_name(user: User) -> str:
    return " ".join(part for part in (user.first_name, user.last_name) if part) or user.email or ""


def user_contact(user: User) -> ContactSchema:
    return ContactSchema(name=user_display_name(user), phone=user.phone, email=user.email)


class UserService:
    def __init__(
        self,
        session: AsyncSession,
        mng_users: UserManager,
        mng_workshops: WorkshopManager,
        svc_cities: CityService,
    ) -> None:
        self._session = session
        self._mng_users = mng_users
        self._mng_workshops = mng_workshops
        self._svc_cities = svc_cities

    async def sync_user(self, current: CurrentUserSchema) -> User:
        """Profile row for the token user. Does not commit: callers do."""
        return await self._mng_users.ensure(
            current.id, email=current.email, first_name=current.first_name, last_name=current.last_name
        )

    async def get_user(self, user_id: UUID) -> User | None:
        return await self._mng_users.get_by_id(user_id)

    async def get_me(self, current: CurrentUserSchema, language: LanguageEnum) -> UserSchema:
        user = await self.sync_user(current)
        await self._session.commit()
        return await self._to_schema(user, current, language)

    async def update_me(self, current: CurrentUserSchema, data: UserUpdateSchema, language: LanguageEnum) -> UserSchema:
        await self._svc_cities.require_active(data.city_id)
        user = await self.sync_user(current)
        for field, value in data.model_dump(by_alias=False).items():
            setattr(user, field, value)
        if user.onboarded_at is None:
            user.onboarded_at = datetime.now(UTC)
        await self._session.commit()
        reloaded = await self._mng_users.get_with_city(user.id)
        return await self._to_schema(reloaded or user, current, language)

    async def _to_schema(self, user: User, current: CurrentUserSchema, language: LanguageEnum) -> UserSchema:
        workshop = await self._mng_workshops.get_by_owner(user.id)
        return UserSchema.model_validate(
            {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "city": user.city,
                "roles": current.roles,
                "onboarded": user.onboarded_at is not None,
                "workshop_status": workshop.status if workshop else None,
            },
            context=language_context(language),
        )
