from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class FilesSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FILES_", env_file=".env", extra="ignore")

    # Local disk storage; mount a persistent volume here in containers
    storage_dir: Path = Path("var/files")
    # Signs download links so <img> tags can load private files without a token
    signing_key: str = Field(default="local-files-signing-key-change-me", min_length=16)
    # Links stay valid at least this long; they change once per window so browsers can cache them
    url_ttl_seconds: int = 3600
    # Absolute API origin for download links, e.g. https://api.sheber.kz
    public_base_url: str = "http://localhost:8000"
