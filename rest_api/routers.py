from fastapi import APIRouter

from rest_api.auth import res_auth
from rest_api.cities import res_cities
from rest_api.designs import res_designs
from rest_api.offers import res_offers
from rest_api.orders import res_orders
from rest_api.system import res_health
from rest_api.users import res_users
from rest_api.workshops import res_workshops

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(res_health.router)
api_v1_router.include_router(res_auth.router)
api_v1_router.include_router(res_cities.router)
api_v1_router.include_router(res_users.router)
api_v1_router.include_router(res_workshops.router)
api_v1_router.include_router(res_designs.router)
api_v1_router.include_router(res_orders.router)
api_v1_router.include_router(res_offers.router)
