import functools

from pydantic_settings import BaseSettings


@functools.cache
def get_settings[TSettings: BaseSettings](cls: type[TSettings]) -> TSettings:
    """Единая точка получения настроек: каждый класс читается из окружения один раз."""
    return cls()
