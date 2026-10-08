import pytest
from alembic import command
from alembic.config import Config

pytestmark = pytest.mark.db


def test_models_match_migrations() -> None:
    """Fails if a model changed without `make migration`."""
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    command.check(config)
