from aioinject import Scoped

from managers.notifications.mng_notifications import NotificationManager
from services.di.types import Providers
from services.notifications.svc_notifications import NotificationService

providers: Providers = [Scoped(NotificationManager), Scoped(NotificationService)]
