from datetime import datetime
from uuid import UUID

from pydantic import Field

from enums.designs_enum import FurnitureTypeEnum
from enums.offers_enum import OfferStatusEnum, OfferTabEnum
from enums.orders_enum import OrderStatusEnum
from schemas.cities.sch_city import CityBriefSchema
from schemas.sch_base import BaseSchema, PageSchema, PaginationSchema
from schemas.workshops.sch_workshop import WorkshopPublicSchema


class OfferSchema(BaseSchema):
    id: UUID
    order_id: UUID
    price: int
    days: int
    comment: str
    warranty_months: int | None
    includes_delivery: bool
    includes_installation: bool
    prepayment_percent: int | None
    status: OfferStatusEnum
    created_at: datetime
    updated_at: datetime


class OfferWithWorkshopSchema(OfferSchema):
    workshop: WorkshopPublicSchema


class OfferOrderBriefSchema(BaseSchema):
    id: UUID
    title: str
    furniture_type: FurnitureTypeEnum
    city: CityBriefSchema
    status: OrderStatusEnum


class MyOfferSchema(OfferSchema):
    order: OfferOrderBriefSchema


class MyOffersFilterSchema(PaginationSchema):
    tab: OfferTabEnum | None = Field(default=None, description="Only offers of this tab")


class OfferTabCountsSchema(BaseSchema):
    active: int
    archive: int


class MyOffersPageSchema(PageSchema[MyOfferSchema]):
    counts: OfferTabCountsSchema = Field(description="Offers in each tab, regardless of the filter")


class OfferCreateSchema(BaseSchema):
    price: int = Field(ge=1000, le=100_000_000, description="KZT")
    days: int = Field(ge=1, le=365)
    comment: str = Field(default="", max_length=2000)
    warranty_months: int | None = Field(default=None, ge=0, le=120)
    includes_delivery: bool = False
    includes_installation: bool = False
    prepayment_percent: int | None = Field(default=None, ge=0, le=100)
