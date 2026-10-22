from aioinject import Scoped

from managers.offers.mng_offers import OfferManager
from services.di.types import Providers
from services.offers.svc_offers import OfferService

providers: Providers = [Scoped(OfferManager), Scoped(OfferService)]
