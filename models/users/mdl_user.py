import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.cities.mdl_city import City
from models.mdl_base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Platform profile on top of the Keycloak account. `id` is the token `sub`."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, sort_order=-10)
    email: Mapped[str | None] = mapped_column(String(320))
    first_name: Mapped[str | None] = mapped_column(String(128))
    last_name: Mapped[str | None] = mapped_column(String(128))
    phone: Mapped[str | None] = mapped_column(String(16))
    city_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("cities.id", ondelete="RESTRICT"), index=True)
    onboarded_at: Mapped[datetime | None]

    city: Mapped[City | None] = relationship(lazy="raise")
