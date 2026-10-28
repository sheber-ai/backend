from datetime import datetime
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import AfterValidator, Field, model_validator

from enums.designs_enum import DesignSourceEnum, FurnitureTypeEnum
from enums.orders_enum import OrderStatusEnum
from schemas.designs.sch_document import DesignDocumentSchema
from schemas.sch_base import BaseSchema


def _validate_document(value: dict[str, Any]) -> dict[str, Any]:
    document = DesignDocumentSchema.model_validate(value).model_dump(mode="json", by_alias=True)
    # Older clients read a missing block as the default; null would break them
    if document.get("hardware") is None:
        document.pop("hardware", None)
    return document


type Document = Annotated[dict[str, Any], AfterValidator(_validate_document)]


class DesignOrderBriefSchema(BaseSchema):
    id: UUID
    status: OrderStatusEnum


class DesignSchema(BaseSchema):
    id: UUID
    title: str
    furniture_type: FurnitureTypeEnum
    source: DesignSourceEnum
    source_url: str | None
    document: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    active_order: DesignOrderBriefSchema | None = Field(
        default=None, description="Unfinished order published from this design"
    )


class DesignCreateSchema(BaseSchema):
    title: str = Field(min_length=1, max_length=128)
    furniture_type: FurnitureTypeEnum
    source: DesignSourceEnum = DesignSourceEnum.SCRATCH
    source_url: str | None = Field(default=None, max_length=2048, pattern=r"^https?://")
    document: Document

    @model_validator(mode="after")
    def _check_source(self) -> Self:
        if self.source == DesignSourceEnum.LINK and not self.source_url:
            raise ValueError("source_url is required for designs created from a link")
        return self


class DesignUpdateSchema(BaseSchema):
    title: str | None = Field(default=None, min_length=1, max_length=128)
    furniture_type: FurnitureTypeEnum | None = None
    document: Document | None = None
