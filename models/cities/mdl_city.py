from typing import Any

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from models.mdl_base import Base, TimestampMixin, UUIDMixin


class City(Base, UUIDMixin, TimestampMixin):
    """Reference table. Rows come from scripts/seeds/cities.json (`make seed`)."""

    __tablename__ = "cities"

    slug: Mapped[str] = mapped_column(String(64), unique=True)
    # {"ru": "Алматы", "kk": "Алматы", "en": "Almaty"}
    name: Mapped[dict[str, Any]]
    # Lower comes first: republican cities, then the rest alphabetically
    sort_order: Mapped[int] = mapped_column(default=100)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)
