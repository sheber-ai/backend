import importlib
import pkgutil

from models.mdl_base import Base


def import_all_models() -> None:
    """Импортирует все модули `models/**/mdl_*.py`, чтобы модели попали в Base.metadata.

    Нужен Alembic (autogenerate видит только зарегистрированные модели) и приложению
    (relationship по строковому имени резолвится только после импорта модели).
    """
    for module in pkgutil.walk_packages(__path__, prefix=f"{__name__}."):
        if module.name.rsplit(".", 1)[-1].startswith("mdl_"):
            importlib.import_module(module.name)


__all__ = ["Base", "import_all_models"]
