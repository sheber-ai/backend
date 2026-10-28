import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from models.mdl_base import Base, TimestampMixin, UUIDMixin


class Notification(Base, UUIDMixin, TimestampMixin):
    """In-app event for one user. The text is built on the frontend from `kind` and the fields."""

    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_user_id_created_at", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # NotificationKindEnum
    kind: Mapped[str] = mapped_column(String(32))
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    # Order title or workshop name the event is about
    subject: Mapped[str] = mapped_column(String(256), default="")
    # Who caused the event: workshop name or client name
    actor: Mapped[str | None] = mapped_column(String(256))
    read_at: Mapped[datetime | None]
