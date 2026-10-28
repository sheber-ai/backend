import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from enums.offers_enum import OfferStatusEnum
from models.mdl_base import Base, TimestampMixin, UUIDMixin
from models.orders.mdl_order import Order
from models.workshops.mdl_workshop import Workshop


class Offer(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "offers"
    __table_args__ = (UniqueConstraint("order_id", "workshop_id"),)

    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    workshop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workshops.id", ondelete="CASCADE"), index=True)
    price: Mapped[int]
    days: Mapped[int]
    comment: Mapped[str] = mapped_column(Text, default="")
    warranty_months: Mapped[int | None]
    includes_delivery: Mapped[bool] = mapped_column(default=False, server_default="false")
    includes_installation: Mapped[bool] = mapped_column(default=False, server_default="false")
    # Share of the price paid before work starts, 0..100
    prepayment_percent: Mapped[int | None]
    # OfferStatusEnum
    status: Mapped[str] = mapped_column(String(32), default=OfferStatusEnum.PENDING, index=True)

    order: Mapped[Order] = relationship(lazy="raise")
    workshop: Mapped[Workshop] = relationship(lazy="raise")
