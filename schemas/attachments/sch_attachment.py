from datetime import datetime
from uuid import UUID

from pydantic import Field

from enums.attachments_enum import AttachmentPurposeEnum
from schemas.sch_base import BaseSchema


class AttachmentSchema(BaseSchema):
    id: UUID
    purpose: AttachmentPurposeEnum
    name: str
    content_type: str
    is_image: bool
    size: int
    width: int | None
    height: int | None
    caption: str
    position: int
    url: str = Field(description="Signed download link; expires, request the list again for a fresh one")
    created_at: datetime


class AttachmentFilterSchema(BaseSchema):
    workshop_id: UUID | None = None
    design_id: UUID | None = None
    order_id: UUID | None = None


class AttachmentUpdateSchema(BaseSchema):
    caption: str = Field(max_length=500)


class AttachmentReorderSchema(BaseSchema):
    ids: list[UUID] = Field(min_length=1, max_length=50)


class AttachmentLimitSchema(BaseSchema):
    purpose: AttachmentPurposeEnum
    max_files: int
    max_bytes: int
    allow_pdf: bool
    public: bool
