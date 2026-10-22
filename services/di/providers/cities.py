from aioinject import Scoped

from managers.cities.mng_cities import CityManager
from services.cities.svc_cities import CityService
from services.di.types import Providers

providers: Providers = [Scoped(CityManager), Scoped(CityService)]
