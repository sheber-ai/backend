from datetime import datetime
from uuid import UUID

from pydantic import Field

from enums.designs_enum import FurnitureTypeEnum
from enums.workshops_enum import WorkshopStatusEnum
from schemas.cities.sch_city import CityBriefSchema
from schemas.sch_base import BaseSchema, PaginationSchema, Phone


class WorkshopPublicSchema(BaseSchema):
    id: UUID
    name: str
    city: CityBriefSchema
    description: str
    website: str | None
    furniture_types: list[FurnitureTypeEnum]
    created_at: datetime


class WorkshopSchema(WorkshopPublicSchema):
    """The owner's and admin's view."""

    phone: str
    tax_id: str
    status: WorkshopStatusEnum
    rejection_reason: str | None
    reviewed_at: datetime | None


class WorkshopAdminSchema(WorkshopSchema):
    owner_email: str | None
    owner_name: str


class WorkshopSaveSchema(BaseSchema):
    name: str = Field(min_length=2, max_length=128)
    city_id: UUID
    phone: Phone
    tax_id: str = Field(pattern=r"^\d{12}$", description="BIN or IIN, 12 digits")
    description: str = Field(default="", max_length=2000)
    website: str | None = Field(default=None, max_length=512, pattern=r"^https?://")
    furniture_types: list[FurnitureTypeEnum] = Field(min_length=1)


class WorkshopRejectSchema(BaseSchema):
    reason: str = Field(min_length=3, max_length=1000)


class WorkshopFilterSchema(PaginationSchema):
    status: WorkshopStatusEnum | None = None
