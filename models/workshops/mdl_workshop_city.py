import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from models.mdl_base import Base


class WorkshopCity(Base):
    """A city the workshop also serves, besides its own `Workshop.city_id`."""

    __tablename__ = "workshop_cities"

    workshop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workshops.id", ondelete="CASCADE"), primary_key=True)
    city_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cities.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
