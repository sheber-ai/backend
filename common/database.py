from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from settings.db_settings import DBSettings
from settings.resolver import get_settings


def create_engine(settings: DBSettings) -> AsyncEngine:
    return create_async_engine(
        settings.url,
        echo=settings.echo,
        pool_size=settings.pool_size,
        max_overflow=settings.max_overflow,
        pool_pre_ping=True,
    )


engine = create_engine(get_settings(DBSettings))

session_maker = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Сессия на один запрос. Незакоммиченное откатывается при закрытии.

    Коммит делает сервис явно (`await self._session.commit()`): так ошибка,
    поднятая после записи, гарантированно не попадёт в БД.
    """
    async with session_maker() as session:
        yield session
