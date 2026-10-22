from enum import StrEnum


class LanguageEnum(StrEnum):
    """Languages of localized reference data. The client sends one in Accept-Language."""

    RU = "ru"
    KK = "kk"
    EN = "en"


DEFAULT_LANGUAGE = LanguageEnum.RU
