import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.mdl_base import Base, TimestampMixin, UUIDMixin


class Message(Base, UUIDMixin, TimestampMixin):
    """Chat line between an order's client and one workshop. A thread is (order_id, workshop_id)."""

    __tablename__ = "messages"
    __table_args__ = (Index("ix_messages_order_id_workshop_id_created_at", "order_id", "workshop_id", "created_at"),)

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    workshop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workshops.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)
    # Set when the other side opens the thread
    read_at: Mapped[datetime | None]
