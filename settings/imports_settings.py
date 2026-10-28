from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ImportsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="IMPORTS_", env_file=".env", extra="ignore")

    # Link reads per user within the window: each one makes the server fetch a foreign site
    rate_limit: int = Field(default=20, ge=1)
    rate_window_seconds: int = Field(default=600, ge=1)
