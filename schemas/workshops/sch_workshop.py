from datetime import date, datetime
from uuid import UUID

from pydantic import Field, field_validator

from enums.designs_enum import FurnitureTypeEnum
from enums.workshops_enum import WorkshopMaterialEnum, WorkshopServiceEnum, WorkshopStatusEnum
from schemas.cities.sch_city import CityBriefSchema
from schemas.sch_base import BaseSchema, PaginationSchema, Phone


class WorkshopPublicSchema(BaseSchema):
    id: UUID
    name: str
    city: CityBriefSchema
    service_cities: list[CityBriefSchema] = Field(description="Other cities the workshop serves besides `city`")
    description: str
    website: str | None
    furniture_types: list[FurnitureTypeEnum]
    services: list[WorkshopServiceEnum]
    materials: list[WorkshopMaterialEnum]
    warranty_months: int | None
    founded_year: int | None
    created_at: datetime


class WorkshopProfileSchema(WorkshopPublicSchema):
    """Public page of an approved workshop. Figures come from orders on the platform only."""

    completed_orders: int
    reviews_count: int
    rating_average: float | None = Field(description="Mean of real reviews, None without reviews")
    verified_at: datetime | None = Field(description="When moderation approved the workshop")


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
    service_city_ids: list[UUID] = Field(
        default_factory=list, max_length=20, description="Other cities served; the main city is ignored here"
    )
    phone: Phone
    tax_id: str = Field(pattern=r"^\d{12}$", description="BIN or IIN, 12 digits")
    description: str = Field(default="", max_length=2000)
    website: str | None = Field(default=None, max_length=512, pattern=r"^https?://")
    furniture_types: list[FurnitureTypeEnum] = Field(min_length=1)
    services: list[WorkshopServiceEnum] = Field(default_factory=list)
    materials: list[WorkshopMaterialEnum] = Field(default_factory=list)
    warranty_months: int | None = Field(default=None, ge=0, le=120)
    founded_year: int | None = Field(default=None, ge=1950)

    @field_validator("founded_year")
    @classmethod
    def _check_year(cls, value: int | None) -> int | None:
        if value is not None and value > date.today().year:
            raise ValueError("founded_year is in the future")
        return value

    @field_validator("furniture_types", "services", "materials")
    @classmethod
    def _unique(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(value))


class WorkshopRejectSchema(BaseSchema):
    reason: str = Field(min_length=3, max_length=1000)


class WorkshopFilterSchema(PaginationSchema):
    status: WorkshopStatusEnum | None = None
