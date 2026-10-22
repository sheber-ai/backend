from aioinject import Scoped

from managers.designs.mng_designs import DesignManager
from services.designs.svc_designs import DesignService
from services.di.types import Providers

providers: Providers = [Scoped(DesignManager), Scoped(DesignService)]
