import uuid
from datetime import date
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enums.orders_enum import OrderStatusEnum
from models.cities.mdl_city import City
from models.mdl_base import Base, TimestampMixin, UUIDMixin
from models.users.mdl_user import User
from models.workshops.mdl_workshop import Workshop


class Order(Base, UUIDMixin, TimestampMixin):
    """Published design. `document` is a snapshot, so later design edits do not change the order."""

    __tablename__ = "orders"

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    design_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("designs.id", ondelete="SET NULL"), index=True)
    workshop_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("workshops.id", ondelete="SET NULL"), index=True)
    city_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), index=True)
    title: Mapped[str] = mapped_column(String(128))
    # FurnitureTypeEnum
    furniture_type: Mapped[str] = mapped_column(String(32), index=True)
    document: Mapped[dict[str, Any]]
    source_url: Mapped[str | None] = mapped_column(String(2048))
    description: Mapped[str] = mapped_column(Text, default="")
    budget: Mapped[int | None]
    deadline: Mapped[date | None]
    # OrderStatusEnum
    status: Mapped[str] = mapped_column(String(32), default=OrderStatusEnum.PUBLISHED, index=True)

    client: Mapped[User] = relationship(lazy="raise")
    workshop: Mapped[Workshop | None] = relationship(lazy="raise")
    city: Mapped[City] = relationship(lazy="raise")
