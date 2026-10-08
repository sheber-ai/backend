import pytest
from alembic import command
from alembic.config import Config

pytestmark = pytest.mark.db


def test_models_match_migrations() -> None:
    """Миграции догоняют БД до head, после чего модели не должны расходиться со схемой.

    Падение значит: модель изменили, а `make migration m="..."` не запустили.
    """
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.check(config)
