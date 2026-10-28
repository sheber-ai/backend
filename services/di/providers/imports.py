from aioinject import Scoped, Singleton

from common.imports.safe_fetch import SafeFetcher
from managers.imports.mng_import_requests import ImportRequestManager
from services.di.types import Providers
from services.imports.svc_imports import ImportService


def create_safe_fetcher() -> SafeFetcher:
    # Defaults: real DNS and network; tests override the whole fetcher
    return SafeFetcher()


providers: Providers = [Singleton(create_safe_fetcher), Scoped(ImportRequestManager), Scoped(ImportService)]
