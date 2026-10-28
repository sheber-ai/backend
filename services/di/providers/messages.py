from aioinject import Scoped

from managers.messages.mng_messages import MessageManager
from services.di.types import Providers
from services.messages.svc_messages import MessageService

providers: Providers = [Scoped(MessageManager), Scoped(MessageService)]
