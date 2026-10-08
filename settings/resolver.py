import functools

from pydantic_settings import BaseSettings


@functools.cache
def get_settings[TSettings: BaseSettings](cls: type[TSettings]) -> TSettings:
    return cls()
