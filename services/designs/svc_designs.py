from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import PermissionDeniedError
from enums.orders_enum import OrderStatusEnum
from managers.designs.mng_designs import DesignManager
from managers.orders.mng_orders import OrderManager
from models.designs.mdl_design import Design
from models.orders.mdl_order import Order
from schemas.auth.sch_auth import CurrentUserSchema
from schemas.designs.sch_design import (
    DesignCreateSchema,
    DesignOrderBriefSchema,
    DesignSchema,
    DesignUpdateSchema,
)
from schemas.sch_base import PageSchema, PaginationSchema
from services.attachments.svc_attachments import AttachmentService
from services.users.svc_users import UserService


class DesignService:
    def __init__(
        self,
        session: AsyncSession,
        mng_designs: DesignManager,
        mng_orders: OrderManager,
        svc_users: UserService,
        svc_attachments: AttachmentService,
    ) -> None:
        self._session = session
        self._mng_designs = mng_designs
        self._mng_orders = mng_orders
        self._svc_users = svc_users
        self._svc_attachments = svc_attachments

    async def get_own(self, current: CurrentUserSchema, design_id: UUID) -> Design:
        design = await self._mng_designs.get_by_id_or_raise(design_id)
        if design.owner_id != current.id:
            raise PermissionDeniedError("Not your design")
        return design

    async def list_designs(self, current: CurrentUserSchema, pagination: PaginationSchema) -> PageSchema[DesignSchema]:
        items, total = await self._mng_designs.list_by_owner(
            current.id, offset=pagination.offset, limit=pagination.limit
        )
        active = await self._mng_orders.active_by_designs([design.id for design in items])
        return PageSchema(items=[self._to_schema(design, active.get(design.id)) for design in items], total=total)

    async def create_design(self, current: CurrentUserSchema, data: DesignCreateSchema) -> DesignSchema:
        await self._svc_users.sync_user(current)
        design = await self._mng_designs.add(Design(owner_id=current.id, **data.model_dump(by_alias=False)))
        await self._session.commit()
        return DesignSchema.model_validate(design)

    async def get_design(self, current: CurrentUserSchema, design_id: UUID) -> DesignSchema:
        design = await self.get_own(current, design_id)
        active = await self._mng_orders.active_by_designs([design.id])
        return self._to_schema(design, active.get(design.id))

    async def update_design(
        self, current: CurrentUserSchema, design_id: UUID, data: DesignUpdateSchema
    ) -> DesignSchema:
        design = await self.get_own(current, design_id)
        for field, value in data.model_dump(by_alias=False, exclude_unset=True, exclude_none=True).items():
            setattr(design, field, value)
        await self._session.commit()
        return DesignSchema.model_validate(design)

    async def delete_design(self, current: CurrentUserSchema, design_id: UUID) -> None:
        design = await self.get_own(current, design_id)
        keys = await self._svc_attachments.storage_keys(design_id=design.id)
        await self._mng_designs.delete(design)
        await self._session.commit()
        # Rows went with the design (cascade); blobs still used by published orders stay
        await self._svc_attachments.purge_blobs(keys)

    async def get_active_order(self, design_id: UUID) -> Order | None:
        return (await self._mng_orders.active_by_designs([design_id])).get(design_id)

    @staticmethod
    def _to_schema(design: Design, active: Order | None) -> DesignSchema:
        schema = DesignSchema.model_validate(design)
        if active is not None:
            schema.active_order = DesignOrderBriefSchema(id=active.id, status=OrderStatusEnum(active.status))
        return schema
