from typing import Annotated
from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Query, status

from rest_api.dependencies import CurrentUser, Language
from schemas.messages.sch_message import (
    MessageCreateSchema,
    MessageSchema,
    MessageThreadSchema,
    ThreadFilterSchema,
    ThreadSchema,
)
from schemas.sch_base import PageSchema
from services.messages.svc_messages import MessageService

router = APIRouter(prefix="/orders/{order_id}", tags=["messages"])


@router.get("/threads")
@inject
async def list_order_threads(
    order_id: UUID, user: CurrentUser, language: Language, svc_messages: Injected[MessageService]
) -> PageSchema[ThreadSchema]:
    return await svc_messages.list_order_threads(user, order_id, language)


@router.get("/messages")
@inject
async def get_order_thread(
    order_id: UUID,
    filters: Annotated[ThreadFilterSchema, Query()],
    user: CurrentUser,
    language: Language,
    svc_messages: Injected[MessageService],
) -> MessageThreadSchema:
    return await svc_messages.get_order_thread(user, order_id, filters, language)


@router.post("/messages", status_code=status.HTTP_201_CREATED)
@inject
async def send_order_message(
    order_id: UUID, body: MessageCreateSchema, user: CurrentUser, svc_messages: Injected[MessageService]
) -> MessageSchema:
    return await svc_messages.send_order_message(user, order_id, body)
