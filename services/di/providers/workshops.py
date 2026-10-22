from aioinject import Scoped, Singleton

from common.security.keycloak_admin import KeycloakAdminClient, RoleGranter
from managers.workshops.mng_workshops import WorkshopManager
from services.di.types import Providers
from services.workshops.svc_workshops import WorkshopService

providers: Providers = [
    Singleton(KeycloakAdminClient, interface=RoleGranter),
    Scoped(WorkshopManager),
    Scoped(WorkshopService),
]
