import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Стабильные имена индексов и ограничений: без них autogenerate не сможет
# корректно сравнивать и удалять constraints между миграциями.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    type_annotation_map = {  # noqa: RUF012
        datetime: DateTime(timezone=True),
        dict[str, Any]: JSONB,
        list[Any]: JSONB,
        # Enum хранится строкой (значением), а не нативным типом Postgres:
        # изменения нативных enum autogenerate не отслеживает.
        enum.Enum: SAEnum(
            enum.Enum,
            native_enum=False,
            length=64,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
    }


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid(), sort_order=-10
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), sort_order=10)
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now(), sort_order=10)
