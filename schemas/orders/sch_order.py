from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from enums.designs_enum import FurnitureTypeEnum
from enums.offers_enum import OfferStatusEnum
from enums.orders_enum import OrderGroupEnum, OrderStatusEnum
from schemas.cities.sch_city import CityBriefSchema
from schemas.offers.sch_offer import OfferSchema
from schemas.sch_base import BaseSchema, PageSchema, PaginationSchema
from schemas.users.sch_user import ContactSchema
from schemas.workshops.sch_workshop import WorkshopPublicSchema


class OrderSchema(BaseSchema):
    id: UUID
    title: str
    furniture_type: FurnitureTypeEnum
    document: dict[str, Any]
    source_url: str | None
    city: CityBriefSchema
    description: str
    budget: int | None
    deadline: date | None
    status: OrderStatusEnum
    offers_count: int
    created_at: datetime


class OrderFeedItemSchema(OrderSchema):
    my_offer_status: OfferStatusEnum | None


class OrderDetailSchema(OrderSchema):
    design_id: UUID | None
    is_owner: bool
    workshop: WorkshopPublicSchema | None
    my_offer: OfferSchema | None
    contact: ContactSchema | None = Field(description="The other side, once a workshop is chosen")


class OrderCreateSchema(BaseSchema):
    design_id: UUID
    city_id: UUID
    description: str = Field(default="", max_length=3000)
    budget: int | None = Field(default=None, ge=0, le=100_000_000, description="KZT")
    deadline: date | None = None

    @field_validator("deadline")
    @classmethod
    def _check_deadline(cls, value: date | None) -> date | None:
        if value is not None and value < date.today():
            raise ValueError("deadline is in the past")
        return value


class MyOrdersFilterSchema(PaginationSchema):
    group: OrderGroupEnum | None = Field(default=None, description="Only orders of this tab")


class OrderGroupCountsSchema(BaseSchema):
    active: int
    completed: int
    cancelled: int


class MyOrdersPageSchema(PageSchema[OrderSchema]):
    counts: OrderGroupCountsSchema = Field(description="Orders in each tab, regardless of the filter")


class OrderFeedFilterSchema(PaginationSchema):
    city_id: UUID | None = None
    furniture_type: FurnitureTypeEnum | None = None
    without_my_offer: bool = Field(default=False, description="Hide orders the workshop already responded to")
    my_cities: bool = Field(default=False, description="Only orders from the cities the workshop serves")
