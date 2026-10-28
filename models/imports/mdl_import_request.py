import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from models.mdl_base import Base, UUIDMixin


class ImportRequest(Base, UUIDMixin):
    """One attempt to read a shop page or its images; rows older than the rate window are purged."""

    __tablename__ = "import_requests"
    __table_args__ = (Index("ix_import_requests_user_id_created_at", "user_id", "created_at"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(32))  # ImportKindEnum
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
