from schemas.system.sch_health import HealthSchema
from settings.app_settings import AppSettings


class HealthService:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings

    async def get_health(self) -> HealthSchema:
        return HealthSchema(status="ok", env=self._settings.env)
