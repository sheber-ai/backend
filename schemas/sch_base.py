from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    """camelCase in JSON, snake_case in Python."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )


class PageSchema[ItemT](BaseSchema):
    items: list[ItemT]
    total: int


class ErrorSchema(BaseSchema):
    code: str
    detail: str
