from aioinject import Scoped

from managers.reviews.mng_reviews import ReviewManager
from services.di.types import Providers
from services.reviews.svc_reviews import ReviewService

providers: Providers = [Scoped(ReviewManager), Scoped(ReviewService)]
