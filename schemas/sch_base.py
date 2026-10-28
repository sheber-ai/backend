import re
from typing import Annotated, Any

import phonenumbers
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, ValidationInfo
from pydantic.alias_generators import to_camel

from common.i18n import localize
from enums.i18n_enum import DEFAULT_LANGUAGE, LanguageEnum


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


def _normalize_phone(value: str) -> str:
    """Any valid number in E.164 (+77011234567). Without "+" the number is read as Kazakhstani: 8 701..., 701..."""
    raw = value.strip()
    digits = re.sub(r"\D", "", raw)
    if not raw.startswith("+"):
        if len(digits) == 11 and digits[0] in "78":
            digits = digits[1:]
        if len(digits) != 10:
            raise ValueError("phone must be international (+country code) or a Kazakhstan number")
        digits = f"7{digits}"
    try:
        number = phonenumbers.parse(f"+{digits}", None)
    except phonenumbers.NumberParseException as error:
        raise ValueError("phone is not a valid number") from error
    if not phonenumbers.is_valid_number(number):
        raise ValueError("phone is not a valid number")
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


type Phone = Annotated[str, AfterValidator(_normalize_phone)]


class PaginationSchema(BaseSchema):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)


class LocalizedTextSchema(BaseSchema):
    """Translations of one text. Russian is required: it is the fallback for missing languages."""

    ru: str = Field(min_length=1, max_length=256)
    kk: str | None = Field(default=None, max_length=256)
    en: str | None = Field(default=None, max_length=256)


def _localize(value: Any, info: ValidationInfo) -> Any:
    if isinstance(value, dict):
        language = (info.context or {}).get("language", DEFAULT_LANGUAGE)
        return localize(value, LanguageEnum(language))
    return value


type LocalizedStr = Annotated[str, BeforeValidator(_localize)]
"""Stored as {"ru": ..., "kk": ...}; validated into one string for `context={"language": ...}`."""


def language_context(language: LanguageEnum) -> dict[str, Any]:
    """Validation context for schemas with LocalizedStr fields."""
    return {"language": language}
