from uuid import UUID

from pydantic import Field

from enums.auth_enum import UserRoleEnum
from enums.workshops_enum import WorkshopStatusEnum
from schemas.cities.sch_city import CityBriefSchema
from schemas.sch_base import BaseSchema, Phone


class UserSchema(BaseSchema):
    id: UUID
    email: str | None
    first_name: str | None
    last_name: str | None
    phone: str | None
    city: CityBriefSchema | None
    roles: list[UserRoleEnum]
    onboarded: bool
    workshop_status: WorkshopStatusEnum | None


class UserUpdateSchema(BaseSchema):
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str | None = Field(default=None, max_length=128)
    phone: Phone
    city_id: UUID


class ContactSchema(BaseSchema):
    """Shown to the other side of an order only after a workshop is chosen."""

    name: str
    phone: str | None
    email: str | None
