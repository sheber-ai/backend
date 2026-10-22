from uuid import UUID

from pydantic import Field

from schemas.sch_base import BaseSchema, LocalizedStr, LocalizedTextSchema


class CityBriefSchema(BaseSchema):
    """City inside other resources; `name` is in the request language."""

    id: UUID
    name: LocalizedStr


class CitySchema(CityBriefSchema):
    slug: str


class CitySeedSchema(BaseSchema):
    slug: str = Field(pattern=r"^[a-z0-9-]{2,64}$")
    name: LocalizedTextSchema
    sort_order: int = Field(default=100, ge=0)
