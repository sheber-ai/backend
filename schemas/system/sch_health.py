from typing import Literal

from schemas.sch_base import BaseSchema
from settings.app_settings import Environment


class HealthSchema(BaseSchema):
    status: Literal["ok"]
    env: Environment
