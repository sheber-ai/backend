from typing import Annotated
from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Query, status

from rest_api.dependencies import CurrentUser
from schemas.designs.sch_design import DesignCreateSchema, DesignSchema, DesignUpdateSchema
from schemas.sch_base import PageSchema, PaginationSchema
from services.designs.svc_designs import DesignService

router = APIRouter(prefix="/designs", tags=["designs"])


@router.get("")
@inject
async def list_designs(
    pagination: Annotated[PaginationSchema, Query()], user: CurrentUser, svc_designs: Injected[DesignService]
) -> PageSchema[DesignSchema]:
    return await svc_designs.list_designs(user, pagination)


@router.post("", status_code=status.HTTP_201_CREATED)
@inject
async def create_design(
    body: DesignCreateSchema, user: CurrentUser, svc_designs: Injected[DesignService]
) -> DesignSchema:
    return await svc_designs.create_design(user, body)


@router.get("/{design_id}")
@inject
async def get_design(design_id: UUID, user: CurrentUser, svc_designs: Injected[DesignService]) -> DesignSchema:
    return await svc_designs.get_design(user, design_id)


@router.patch("/{design_id}")
@inject
async def update_design(
    design_id: UUID, body: DesignUpdateSchema, user: CurrentUser, svc_designs: Injected[DesignService]
) -> DesignSchema:
    return await svc_designs.update_design(user, design_id, body)


@router.delete("/{design_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_design(design_id: UUID, user: CurrentUser, svc_designs: Injected[DesignService]) -> None:
    await svc_designs.delete_design(user, design_id)
