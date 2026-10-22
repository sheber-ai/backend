from aioinject import Scoped

from managers.orders.mng_orders import OrderManager
from services.di.types import Providers
from services.orders.svc_orders import OrderService

providers: Providers = [Scoped(OrderManager), Scoped(OrderService)]
