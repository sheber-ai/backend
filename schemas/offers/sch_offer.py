from datetime import datetime
from uuid import UUID

from pydantic import Field

from enums.designs_enum import FurnitureTypeEnum
from enums.offers_enum import OfferStatusEnum
from enums.orders_enum import OrderStatusEnum
from schemas.cities.sch_city import CityBriefSchema
from schemas.sch_base import BaseSchema
from schemas.workshops.sch_workshop import WorkshopPublicSchema


class OfferSchema(BaseSchema):
    id: UUID
    order_id: UUID
    price: int
    days: int
    comment: str
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


class OfferCreateSchema(BaseSchema):
    price: int = Field(ge=1000, le=100_000_000, description="KZT")
    days: int = Field(ge=1, le=365)
    comment: str = Field(default="", max_length=2000)
