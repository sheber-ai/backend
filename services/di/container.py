import functools
import importlib
import pkgutil
from collections.abc import Iterator

import aioinject
from aioinject.ext.fastapi import FastAPIExtension
from pydantic_settings import BaseSettings
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import get_session
from services.di import providers as providers_package
from services.di.types import Providers
from settings.app_settings import AppSettings
from settings.db_settings import DBSettings
from settings.resolver import get_settings

SETTINGS_CLASSES: tuple[type[BaseSettings], ...] = (AppSettings, DBSettings)


def _discover_providers() -> Iterator[Providers]:
    """Собирает `providers` из каждого модуля services/di/providers/<домен>.py."""
    for module_info in pkgutil.iter_modules(providers_package.__path__):
        module = importlib.import_module(f"{providers_package.__name__}.{module_info.name}")
        yield module.providers


@functools.cache
def create_container() -> aioinject.Container:
    container = aioinject.Container(extensions=[FastAPIExtension()])

    for settings_cls in SETTINGS_CLASSES:
        container.register(aioinject.Singleton(functools.partial(get_settings, settings_cls), interface=settings_cls))

    container.register(aioinject.Scoped(get_session, interface=AsyncSession))

    for providers in _discover_providers():
        container.register(*providers)

    return container
