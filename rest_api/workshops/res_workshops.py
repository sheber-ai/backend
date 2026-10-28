from typing import Annotated
from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Query

from rest_api.dependencies import AdminUser, CurrentUser, Language
from schemas.sch_base import PageSchema
from schemas.workshops.sch_workshop import (
    WorkshopAdminSchema,
    WorkshopFilterSchema,
    WorkshopProfileSchema,
    WorkshopRejectSchema,
    WorkshopSaveSchema,
    WorkshopSchema,
)
from services.workshops.svc_workshops import WorkshopService

router = APIRouter(prefix="/workshops", tags=["workshops"])


@router.get("/mine")
@inject
async def get_my_workshop(
    user: CurrentUser, language: Language, svc_workshops: Injected[WorkshopService]
) -> WorkshopSchema:
    return await svc_workshops.get_my_workshop(user, language)


@router.put("/mine")
@inject
async def save_my_workshop(
    body: WorkshopSaveSchema, user: CurrentUser, language: Language, svc_workshops: Injected[WorkshopService]
) -> WorkshopSchema:
    return await svc_workshops.save_my_workshop(user, body, language)


@router.get("")
@inject
async def list_workshops(
    filters: Annotated[WorkshopFilterSchema, Query()],
    _: AdminUser,
    language: Language,
    svc_workshops: Injected[WorkshopService],
) -> PageSchema[WorkshopAdminSchema]:
    return await svc_workshops.list_workshops(filters, language)


@router.get("/{workshop_id}")
@inject
async def get_workshop(
    workshop_id: UUID, language: Language, svc_workshops: Injected[WorkshopService]
) -> WorkshopProfileSchema:
    return await svc_workshops.get_workshop(workshop_id, language)


@router.post("/{workshop_id}/approve")
@inject
async def approve_workshop(
    workshop_id: UUID, _: AdminUser, language: Language, svc_workshops: Injected[WorkshopService]
) -> WorkshopSchema:
    return await svc_workshops.approve_workshop(workshop_id, language)


@router.post("/{workshop_id}/reject")
@inject
async def reject_workshop(
    workshop_id: UUID,
    body: WorkshopRejectSchema,
    _: AdminUser,
    language: Language,
    svc_workshops: Injected[WorkshopService],
) -> WorkshopSchema:
    return await svc_workshops.reject_workshop(workshop_id, body, language)
