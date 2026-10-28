from typing import Annotated
from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Query

from rest_api.dependencies import CurrentUser
from schemas.notifications.sch_notification import (
    NotificationFilterSchema,
    NotificationSchema,
    NotificationSummarySchema,
)
from schemas.sch_base import PageSchema
from services.notifications.svc_notifications import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
@inject
async def list_notifications(
    filters: Annotated[NotificationFilterSchema, Query()],
    user: CurrentUser,
    svc_notifications: Injected[NotificationService],
) -> PageSchema[NotificationSchema]:
    return await svc_notifications.list_notifications(user, filters)


@router.get("/summary")
@inject
async def get_notification_summary(
    user: CurrentUser, svc_notifications: Injected[NotificationService]
) -> NotificationSummarySchema:
    return await svc_notifications.get_notification_summary(user)


@router.post("/read-all")
@inject
async def read_all_notifications(
    user: CurrentUser, svc_notifications: Injected[NotificationService]
) -> NotificationSummarySchema:
    return await svc_notifications.read_all_notifications(user)


@router.post("/{notification_id}/read")
@inject
async def read_notification(
    notification_id: UUID, user: CurrentUser, svc_notifications: Injected[NotificationService]
) -> NotificationSchema:
    return await svc_notifications.read_notification(user, notification_id)
