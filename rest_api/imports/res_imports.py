from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter

from rest_api.dependencies import CurrentUser
from schemas.imports.sch_import import (
    ImportImagesRequestSchema,
    ImportImagesResultSchema,
    ImportPreviewRequestSchema,
    ImportPreviewSchema,
)
from services.imports.svc_imports import ImportService

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/preview")
@inject
async def preview_import(
    body: ImportPreviewRequestSchema, user: CurrentUser, svc_imports: Injected[ImportService]
) -> ImportPreviewSchema:
    return await svc_imports.preview_import(user, body)


@router.post("/images")
@inject
async def import_images(
    body: ImportImagesRequestSchema, user: CurrentUser, svc_imports: Injected[ImportService]
) -> ImportImagesResultSchema:
    return await svc_imports.import_images(user, body)
