from typing import Annotated
from uuid import UUID

from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter, Query

from rest_api.dependencies import ContractorUser, CurrentUser
from schemas.reviews.sch_review import ReviewReplySchema, ReviewSaveSchema, ReviewSchema
from schemas.sch_base import PageSchema, PaginationSchema
from services.reviews.svc_reviews import ReviewService

router = APIRouter(tags=["reviews"])


@router.put("/orders/{order_id}/review")
@inject
async def save_review(
    order_id: UUID, body: ReviewSaveSchema, user: CurrentUser, svc_reviews: Injected[ReviewService]
) -> ReviewSchema:
    return await svc_reviews.save_review(user, order_id, body)


@router.put("/orders/{order_id}/review/reply")
@inject
async def reply_to_review(
    order_id: UUID, body: ReviewReplySchema, user: ContractorUser, svc_reviews: Injected[ReviewService]
) -> ReviewSchema:
    return await svc_reviews.reply_to_review(user, order_id, body)


@router.get("/orders/{order_id}/review")
@inject
async def get_order_review(
    order_id: UUID, user: CurrentUser, svc_reviews: Injected[ReviewService]
) -> ReviewSchema | None:
    return await svc_reviews.get_order_review(user, order_id)


@router.get("/workshops/{workshop_id}/reviews")
@inject
async def list_workshop_reviews(
    workshop_id: UUID,
    pagination: Annotated[PaginationSchema, Query()],
    svc_reviews: Injected[ReviewService],
) -> PageSchema[ReviewSchema]:
    return await svc_reviews.list_workshop_reviews(workshop_id, pagination)
