from typing import Annotated
from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, File, Form, Query, Response, UploadFile, status

from enums.attachments_enum import AttachmentPurposeEnum
from rest_api.dependencies import CurrentUser, OptionalUser
from schemas.attachments.sch_attachment import (
    AttachmentFilterSchema,
    AttachmentLimitSchema,
    AttachmentReorderSchema,
    AttachmentSchema,
    AttachmentUpdateSchema,
)
from schemas.sch_base import PageSchema
from services.attachments.svc_attachments import AttachmentService

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.get("/limits")
async def list_attachment_limits() -> list[AttachmentLimitSchema]:
    return AttachmentService.list_attachment_limits()


@router.get("")
@inject
async def list_attachments(
    filters: Annotated[AttachmentFilterSchema, Query()],
    user: OptionalUser,
    svc_attachments: Injected[AttachmentService],
) -> PageSchema[AttachmentSchema]:
    return await svc_attachments.list_attachments(user, filters)


@router.post("", status_code=status.HTTP_201_CREATED)
@inject
async def upload_attachment(
    file: Annotated[UploadFile, File()],
    purpose: Annotated[AttachmentPurposeEnum, Form()],
    user: CurrentUser,
    svc_attachments: Injected[AttachmentService],
    design_id: Annotated[UUID | None, Form(alias="designId")] = None,
    order_id: Annotated[UUID | None, Form(alias="orderId")] = None,
) -> AttachmentSchema:
    return await svc_attachments.upload_attachment(user, purpose, file, design_id, order_id)


@router.post("/reorder")
@inject
async def reorder_attachments(
    body: AttachmentReorderSchema, user: CurrentUser, svc_attachments: Injected[AttachmentService]
) -> PageSchema[AttachmentSchema]:
    return await svc_attachments.reorder_attachments(user, body)


@router.patch("/{attachment_id}")
@inject
async def update_attachment(
    attachment_id: UUID, body: AttachmentUpdateSchema, user: CurrentUser, svc_attachments: Injected[AttachmentService]
) -> AttachmentSchema:
    return await svc_attachments.update_attachment(user, attachment_id, body)


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_attachment(
    attachment_id: UUID, user: CurrentUser, svc_attachments: Injected[AttachmentService]
) -> None:
    await svc_attachments.delete_attachment(user, attachment_id)


@router.get(
    "/{attachment_id}/content",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
@inject
async def get_attachment_content(
    attachment_id: UUID,
    expires: int,
    signature: str,
    svc_attachments: Injected[AttachmentService],
) -> Response:
    # Protocol endpoint: raw bytes, the signed link replaces the bearer token
    attachment, data = await svc_attachments.read_attachment_content(attachment_id, expires, signature)
    disposition = "inline" if attachment.content_type.startswith("image/") else "attachment"
    return Response(
        content=data,
        media_type=attachment.content_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{attachment.id}{_suffix(attachment.name)}"',
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox; default-src 'none'",
            "Cache-Control": "private, max-age=3600",
        },
    )


def _suffix(name: str) -> str:
    return "." + name.rsplit(".", 1)[-1] if "." in name else ""
