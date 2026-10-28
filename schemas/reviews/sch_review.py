from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from schemas.sch_base import BaseSchema


class ReviewSchema(BaseSchema):
    id: UUID
    order_id: UUID
    rating: int
    text: str
    author: str = Field(description="First name and last-name initial, never the full name")
    reply: str | None
    replied_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ReviewSaveSchema(BaseSchema):
    rating: int = Field(ge=1, le=5)
    text: str = Field(default="", max_length=2000)

    @field_validator("text")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class ReviewReplySchema(BaseSchema):
    text: str = Field(max_length=1000)

    @field_validator("text")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reply is empty")
        return value
