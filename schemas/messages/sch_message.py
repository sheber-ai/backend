from datetime import datetime
from uuid import UUID

from pydantic import Field, field_validator

from enums.messages_enum import MessageAuthorEnum
from enums.offers_enum import OfferStatusEnum
from schemas.sch_base import BaseSchema
from schemas.workshops.sch_workshop import WorkshopPublicSchema


class MessageSchema(BaseSchema):
    id: UUID
    author: MessageAuthorEnum
    is_mine: bool
    body: str
    read_at: datetime | None
    created_at: datetime


class MessageCreateSchema(BaseSchema):
    body: str = Field(min_length=1, max_length=4000)
    workshop_id: UUID | None = Field(default=None, description="Required for the order owner: whom to write")

    @field_validator("body")
    @classmethod
    def _strip(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message is empty")
        return value


class ThreadFilterSchema(BaseSchema):
    workshop_id: UUID | None = Field(default=None, description="Required for the order owner")


class ThreadSchema(BaseSchema):
    workshop: WorkshopPublicSchema
    offer_status: OfferStatusEnum | None
    unread_count: int
    last_message: MessageSchema | None
    can_write: bool


class MessageThreadSchema(BaseSchema):
    workshop: WorkshopPublicSchema
    can_write: bool
    messages: list[MessageSchema]
