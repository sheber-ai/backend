from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from common.exceptions import NotFoundError, PermissionDeniedError, ReviewNotAllowedError
from enums.auth_enum import UserRoleEnum
from enums.notifications_enum import NotificationKindEnum
from enums.orders_enum import OrderStatusEnum
from enums.workshops_enum import WorkshopStatusEnum
from managers.orders.mng_orders import OrderManager
from managers.reviews.mng_reviews import ReviewManager
from managers.users.mng_users import UserManager
from managers.workshops.mng_workshops import WorkshopManager
from models.reviews.mdl_review import Review
from models.users.mdl_user import User
from schemas.auth.sch_auth import CurrentUserSchema
from schemas.reviews.sch_review import ReviewReplySchema, ReviewSaveSchema, ReviewSchema
from schemas.sch_base import PageSchema, PaginationSchema
from services.notifications.svc_notifications import NotificationService


def review_author(user: User | None) -> str:
    """Public name of a reviewer: "Айгерим К." — the full name and contacts stay private."""
    if user is None or not user.first_name:
        return ""
    initial = f" {user.last_name[0]}." if user.last_name else ""
    return f"{user.first_name}{initial}"


def _schema(review: Review, author: User | None) -> ReviewSchema:
    return ReviewSchema(
        id=review.id,
        order_id=review.order_id,
        rating=review.rating,
        text=review.text,
        author=review_author(author),
        reply=review.reply,
        replied_at=review.replied_at,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


class ReviewService:
    def __init__(
        self,
        session: AsyncSession,
        mng_reviews: ReviewManager,
        mng_orders: OrderManager,
        mng_workshops: WorkshopManager,
        mng_users: UserManager,
        svc_notifications: NotificationService,
    ) -> None:
        self._session = session
        self._mng_reviews = mng_reviews
        self._mng_orders = mng_orders
        self._mng_workshops = mng_workshops
        self._mng_users = mng_users
        self._svc_notifications = svc_notifications

    async def save_review(self, current: CurrentUserSchema, order_id: UUID, data: ReviewSaveSchema) -> ReviewSchema:
        """Creates the order's review or lets the client correct it; the workshop is the one that did the job."""
        order = await self._mng_orders.get_by_id_or_raise(order_id)
        if order.client_id != current.id:
            raise PermissionDeniedError("Only the client of the order can review it")
        if order.status != OrderStatusEnum.COMPLETED or order.workshop_id is None:
            raise ReviewNotAllowedError("Reviews open once the order is completed")
        review = await self._mng_reviews.get_by_order(order.id)
        author = await self._mng_users.get_by_id(current.id)
        if review is None:
            review = await self._mng_reviews.add(
                Review(
                    order_id=order.id,
                    workshop_id=order.workshop_id,
                    client_id=current.id,
                    rating=data.rating,
                    text=data.text,
                )
            )
            await self._svc_notifications.notify_workshops(
                [order.workshop_id],
                NotificationKindEnum.REVIEW_RECEIVED,
                subject=order.title,
                order_id=order.id,
                actor=review_author(author),
            )
        else:
            review.rating = data.rating
            review.text = data.text
        await self._session.commit()
        await self._session.refresh(review)
        return _schema(review, author)

    async def reply_to_review(
        self, current: CurrentUserSchema, order_id: UUID, data: ReviewReplySchema
    ) -> ReviewSchema:
        """The workshop that got the review answers it publicly; the answer can be corrected."""
        review = await self._mng_reviews.get_by_order(order_id)
        workshop = await self._mng_workshops.get_by_owner(current.id)
        if review is None or workshop is None or review.workshop_id != workshop.id:
            raise PermissionDeniedError("Only the reviewed workshop can reply")
        if workshop.status != WorkshopStatusEnum.APPROVED:
            raise PermissionDeniedError("Workshop is not approved")
        if review.reply is None:
            order = await self._mng_orders.get_by_id_or_raise(order_id)
            await self._svc_notifications.notify(
                review.client_id,
                NotificationKindEnum.REVIEW_REPLIED,
                subject=order.title,
                order_id=order_id,
                actor=workshop.name,
            )
        review.reply = data.text
        review.replied_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(review)
        return _schema(review, await self._mng_users.get_by_id(review.client_id))

    async def get_order_review(self, current: CurrentUserSchema, order_id: UUID) -> ReviewSchema | None:
        order = await self._mng_orders.get_by_id_or_raise(order_id)
        workshop = await self._mng_workshops.get_by_owner(current.id)
        is_assigned = workshop is not None and order.workshop_id == workshop.id
        if not (order.client_id == current.id or is_assigned or current.has_role(UserRoleEnum.ADMIN)):
            raise PermissionDeniedError("Order is not available")
        review = await self._mng_reviews.get_by_order(order.id)
        if review is None:
            return None
        return _schema(review, await self._mng_users.get_by_id(review.client_id))

    async def list_workshop_reviews(self, workshop_id: UUID, pagination: PaginationSchema) -> PageSchema[ReviewSchema]:
        workshop = await self._mng_workshops.get_by_id(workshop_id)
        if workshop is None or workshop.status != WorkshopStatusEnum.APPROVED:
            raise NotFoundError(f"Workshop {workshop_id} not found")
        items, total = await self._mng_reviews.list_by_workshop(
            workshop_id, offset=pagination.offset, limit=pagination.limit
        )
        return PageSchema(items=[_schema(item, item.client) for item in items], total=total)
