from fastapi import APIRouter

from rest_api.system import res_health

api_v1_router = APIRouter(prefix="/api/v1")

# Каждый новый роутер подключается здесь, по одному на строку.
api_v1_router.include_router(res_health.router)
