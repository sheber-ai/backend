from aioinject import Scoped

from managers.users.mng_users import UserManager
from services.di.types import Providers
from services.users.svc_users import UserService

providers: Providers = [Scoped(UserManager), Scoped(UserService)]
