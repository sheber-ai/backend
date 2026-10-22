import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enums.workshops_enum import WorkshopStatusEnum
from models.cities.mdl_city import City
from models.mdl_base import Base, TimestampMixin, UUIDMixin
from models.users.mdl_user import User


class Workshop(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workshops"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    city_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    phone: Mapped[str] = mapped_column(String(16))
    tax_id: Mapped[str] = mapped_column(String(12))
    description: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str | None] = mapped_column(String(512))
    # FurnitureTypeEnum values
    furniture_types: Mapped[list[Any]] = mapped_column(default=list)
    # WorkshopStatusEnum
    status: Mapped[str] = mapped_column(String(32), default=WorkshopStatusEnum.PENDING, index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None]

    owner: Mapped[User] = relationship(lazy="raise")
    city: Mapped[City] = relationship(lazy="raise")
