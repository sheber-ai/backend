from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import PermissionDeniedError
from managers.designs.mng_designs import DesignManager
from models.designs.mdl_design import Design
from schemas.auth.sch_auth import CurrentUserSchema
from schemas.designs.sch_design import DesignCreateSchema, DesignSchema, DesignUpdateSchema
from schemas.sch_base import PageSchema, PaginationSchema
from services.users.svc_users import UserService


class DesignService:
    def __init__(self, session: AsyncSession, mng_designs: DesignManager, svc_users: UserService) -> None:
        self._session = session
        self._mng_designs = mng_designs
        self._svc_users = svc_users

    async def get_own(self, current: CurrentUserSchema, design_id: UUID) -> Design:
        design = await self._mng_designs.get_by_id_or_raise(design_id)
        if design.owner_id != current.id:
            raise PermissionDeniedError("Not your design")
        return design

    async def list_designs(self, current: CurrentUserSchema, pagination: PaginationSchema) -> PageSchema[DesignSchema]:
        items, total = await self._mng_designs.list_by_owner(
            current.id, offset=pagination.offset, limit=pagination.limit
        )
        return PageSchema(items=[DesignSchema.model_validate(design) for design in items], total=total)

    async def create_design(self, current: CurrentUserSchema, data: DesignCreateSchema) -> DesignSchema:
        await self._svc_users.sync_user(current)
        design = await self._mng_designs.add(Design(owner_id=current.id, **data.model_dump(by_alias=False)))
        await self._session.commit()
        return DesignSchema.model_validate(design)

    async def get_design(self, current: CurrentUserSchema, design_id: UUID) -> DesignSchema:
        return DesignSchema.model_validate(await self.get_own(current, design_id))

    async def update_design(
        self, current: CurrentUserSchema, design_id: UUID, data: DesignUpdateSchema
    ) -> DesignSchema:
        design = await self.get_own(current, design_id)
        for field, value in data.model_dump(by_alias=False, exclude_unset=True, exclude_none=True).items():
            setattr(design, field, value)
        await self._session.commit()
        return DesignSchema.model_validate(design)

    async def delete_design(self, current: CurrentUserSchema, design_id: UUID) -> None:
        await self._mng_designs.delete(await self.get_own(current, design_id))
        await self._session.commit()
