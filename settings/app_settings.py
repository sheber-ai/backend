from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

type Environment = Literal["local", "dev", "stage", "prod"]


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    env: Environment = "local"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]
