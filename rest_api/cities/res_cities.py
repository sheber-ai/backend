from aioinject import Injected
from aioinject.ext.fastapi import inject
from fastapi import APIRouter

from rest_api.dependencies import Language
from schemas.cities.sch_city import CitySchema
from schemas.sch_base import PageSchema
from services.cities.svc_cities import CityService

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("")
@inject
async def list_cities(language: Language, svc_cities: Injected[CityService]) -> PageSchema[CitySchema]:
    return await svc_cities.list_cities(language)
