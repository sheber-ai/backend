from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import NotFoundError, WorkshopRequiredError
from common.security.keycloak_admin import RoleGranter
from enums.auth_enum import UserRoleEnum
from enums.i18n_enum import LanguageEnum
from enums.workshops_enum import WorkshopStatusEnum
from managers.workshops.mng_workshops import WorkshopManager
from models.workshops.mdl_workshop import Workshop
from schemas.auth.sch_auth import CurrentUserSchema
from schemas.sch_base import PageSchema, language_context
from schemas.workshops.sch_workshop import (
    WorkshopAdminSchema,
    WorkshopFilterSchema,
    WorkshopPublicSchema,
    WorkshopRejectSchema,
    WorkshopSaveSchema,
    WorkshopSchema,
)
from services.cities.svc_cities import CityService
from services.users.svc_users import UserService, user_display_name


class WorkshopService:
    def __init__(
        self,
        session: AsyncSession,
        mng_workshops: WorkshopManager,
        svc_users: UserService,
        svc_cities: CityService,
        role_granter: RoleGranter,
    ) -> None:
        self._session = session
        self._mng_workshops = mng_workshops
        self._svc_users = svc_users
        self._svc_cities = svc_cities
        self._role_granter = role_granter

    async def require_approved(self, current: CurrentUserSchema) -> Workshop:
        workshop = await self._mng_workshops.get_by_owner(current.id)
        if workshop is None or workshop.status != WorkshopStatusEnum.APPROVED:
            raise WorkshopRequiredError("An approved workshop is required")
        return workshop

    async def get_approved_or_none(self, user_id: UUID) -> Workshop | None:
        workshop = await self._mng_workshops.get_by_owner(user_id)
        return workshop if workshop and workshop.status == WorkshopStatusEnum.APPROVED else None

    async def get_my_workshop(self, current: CurrentUserSchema, language: LanguageEnum) -> WorkshopSchema:
        workshop = await self._mng_workshops.get_by_owner(current.id)
        if workshop is None:
            raise NotFoundError("Workshop not found")
        return WorkshopSchema.model_validate(workshop, context=language_context(language))

    async def save_my_workshop(
        self, current: CurrentUserSchema, data: WorkshopSaveSchema, language: LanguageEnum
    ) -> WorkshopSchema:
        await self._svc_cities.require_active(data.city_id)
        await self._svc_users.sync_user(current)
        workshop = await self._mng_workshops.get_by_owner(current.id)
        if workshop is None:
            workshop = await self._mng_workshops.add(Workshop(owner_id=current.id, **data.model_dump(by_alias=False)))
        else:
            for field, value in data.model_dump(by_alias=False).items():
                setattr(workshop, field, value)
            if workshop.status == WorkshopStatusEnum.REJECTED:
                workshop.status = WorkshopStatusEnum.PENDING
                workshop.rejection_reason = None
        await self._session.commit()
        return await self._reloaded(workshop.id, language)

    async def get_workshop(self, workshop_id: UUID, language: LanguageEnum) -> WorkshopPublicSchema:
        workshop = await self._mng_workshops.get_with_city(workshop_id)
        if workshop is None or workshop.status != WorkshopStatusEnum.APPROVED:
            raise NotFoundError(f"Workshop {workshop_id} not found")
        return WorkshopPublicSchema.model_validate(workshop, context=language_context(language))

    async def list_workshops(
        self, filters: WorkshopFilterSchema, language: LanguageEnum
    ) -> PageSchema[WorkshopAdminSchema]:
        items, total = await self._mng_workshops.list_with_owner(
            status=filters.status, offset=filters.offset, limit=filters.limit
        )
        context = language_context(language)
        return PageSchema(
            items=[
                WorkshopAdminSchema.model_validate(
                    {
                        **WorkshopSchema.model_validate(workshop, context=context).model_dump(by_alias=False),
                        "owner_email": workshop.owner.email,
                        "owner_name": user_display_name(workshop.owner),
                    }
                )
                for workshop in items
            ],
            total=total,
        )

    async def approve_workshop(self, workshop_id: UUID, language: LanguageEnum) -> WorkshopSchema:
        workshop = await self._mng_workshops.get_by_id_or_raise(workshop_id)
        workshop.status = WorkshopStatusEnum.APPROVED
        workshop.rejection_reason = None
        workshop.reviewed_at = datetime.now(UTC)
        # Grant before commit: if Keycloak is down the approval is rolled back
        await self._role_granter.grant_role(workshop.owner_id, UserRoleEnum.CONTRACTOR)
        await self._session.commit()
        return await self._reloaded(workshop.id, language)

    async def reject_workshop(
        self, workshop_id: UUID, data: WorkshopRejectSchema, language: LanguageEnum
    ) -> WorkshopSchema:
        workshop = await self._mng_workshops.get_by_id_or_raise(workshop_id)
        was_approved = workshop.status == WorkshopStatusEnum.APPROVED
        workshop.status = WorkshopStatusEnum.REJECTED
        workshop.rejection_reason = data.reason
        workshop.reviewed_at = datetime.now(UTC)
        if was_approved:
            await self._role_granter.revoke_role(workshop.owner_id, UserRoleEnum.CONTRACTOR)
        await self._session.commit()
        return await self._reloaded(workshop.id, language)

    async def _reloaded(self, workshop_id: UUID, language: LanguageEnum) -> WorkshopSchema:
        workshop = await self._mng_workshops.get_with_city(workshop_id)
        if workshop is None:
            raise NotFoundError(f"Workshop {workshop_id} not found")
        return WorkshopSchema.model_validate(workshop, context=language_context(language))
