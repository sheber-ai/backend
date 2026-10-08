from fastapi import APIRouter

from rest_api.auth import res_auth
from rest_api.system import res_health

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(res_health.router)
api_v1_router.include_router(res_auth.router)
