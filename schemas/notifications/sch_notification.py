from datetime import datetime
from uuid import UUID

from enums.notifications_enum import NotificationKindEnum
from schemas.sch_base import BaseSchema, PaginationSchema


class NotificationSchema(BaseSchema):
    id: UUID
    kind: NotificationKindEnum
    order_id: UUID | None
    subject: str
    actor: str | None
    read_at: datetime | None
    created_at: datetime


class NotificationSummarySchema(BaseSchema):
    unread: int


class NotificationFilterSchema(PaginationSchema):
    unread_only: bool = False
