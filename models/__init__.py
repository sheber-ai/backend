import importlib
import pkgutil

from models.mdl_base import Base


def import_all_models() -> None:
    """Register every models/**/mdl_*.py in Base.metadata (needed by autogenerate and string relationships)."""
    for module in pkgutil.walk_packages(__path__, prefix=f"{__name__}."):
        if module.name.rsplit(".", 1)[-1].startswith("mdl_"):
            importlib.import_module(module.name)


__all__ = ["Base", "import_all_models"]
