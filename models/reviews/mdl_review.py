import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.mdl_base import Base, TimestampMixin, UUIDMixin
from models.users.mdl_user import User


class Review(Base, UUIDMixin, TimestampMixin):
    """Client's verdict on the workshop that completed the order. One per order."""

    __tablename__ = "reviews"
    __table_args__ = (CheckConstraint("rating BETWEEN 1 AND 5", name="rating_range"),)

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True)
    workshop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workshops.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(SmallInteger)
    text: Mapped[str] = mapped_column(Text, default="")
    # The workshop's public answer, one per review
    reply: Mapped[str | None] = mapped_column(Text)
    replied_at: Mapped[datetime | None]

    client: Mapped[User] = relationship(lazy="raise")
