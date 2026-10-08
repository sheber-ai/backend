from aioinject import Scoped

from services.di.types import Providers
from services.system.svc_health import HealthService

providers: Providers = [
    Scoped(HealthService),
]
