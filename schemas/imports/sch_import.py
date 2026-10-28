from uuid import UUID

from pydantic import Field

from schemas.attachments.sch_attachment import AttachmentSchema
from schemas.sch_base import BaseSchema


class ImportPreviewRequestSchema(BaseSchema):
    url: str = Field(min_length=4, max_length=2048)


class ImportSizeSchema(BaseSchema):
    """Millimetres, as far as the shop published them."""

    width: int | None
    height: int | None
    depth: int | None


class ImportPreviewSchema(BaseSchema):
    url: str = Field(description="Normalised link that was read")
    source: str = Field(description="Shop host, e.g. www.ikea.com")
    site_name: str | None
    title: str | None
    description: str | None
    images: list[str] = Field(description="Absolute image links from the page, at most 6")
    price: float | None
    currency: str | None
    brand: str | None
    size: ImportSizeSchema | None
    structured: bool = Field(description="The page describes a schema.org Product, not just Open Graph tags")


class ImportImagesRequestSchema(BaseSchema):
    design_id: UUID
    image_urls: list[str] = Field(min_length=1, max_length=6)
    source: str = Field(default="", max_length=256, description="Shown as the caption, e.g. the shop name")


class ImportImagesResultSchema(BaseSchema):
    attached: list[AttachmentSchema]
    failed: int = Field(description="Images the shop did not give or that are not real images")
