import uuid
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from enums.designs_enum import DesignSourceEnum
from models.mdl_base import Base, TimestampMixin, UUIDMixin


class Design(Base, UUIDMixin, TimestampMixin):
    """Furniture project edited in the constructor. `document` follows DesignDocumentSchema."""

    __tablename__ = "designs"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    # FurnitureTypeEnum
    furniture_type: Mapped[str] = mapped_column(String(32))
    # DesignSourceEnum
    source: Mapped[str] = mapped_column(String(32), default=DesignSourceEnum.SCRATCH)
    source_url: Mapped[str | None] = mapped_column(String(2048))
    document: Mapped[dict[str, Any]]
