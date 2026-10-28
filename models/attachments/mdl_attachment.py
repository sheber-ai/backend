import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from models.mdl_base import Base, TimestampMixin, UUIDMixin


class Attachment(Base, UUIDMixin, TimestampMixin):
    """Uploaded file bound to exactly one of: workshop, design, order.

    Orders get copies of design rows when published; copies share `storage_key`,
    so a blob is removed only when no row points at it.
    """

    __tablename__ = "attachments"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # AttachmentPurposeEnum
    purpose: Mapped[str] = mapped_column(String(32))
    workshop_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workshops.id", ondelete="CASCADE"), index=True)
    design_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("designs.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    storage_key: Mapped[str] = mapped_column(String(128), index=True)
    content_type: Mapped[str] = mapped_column(String(64))
    size: Mapped[int]
    # Shown to people only; never used to build paths
    name: Mapped[str] = mapped_column(String(256))
    width: Mapped[int | None]
    height: Mapped[int | None]
    caption: Mapped[str] = mapped_column(String(500), default="")
    position: Mapped[int] = mapped_column(default=0)
