from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter

from schemas.system.sch_health import HealthSchema
from services.system.svc_health import HealthService

router = APIRouter(prefix="/health", tags=["system"])


@router.get("")
@inject
async def get_health(svc_health: Injected[HealthService]) -> HealthSchema:
    return await svc_health.get_health()
