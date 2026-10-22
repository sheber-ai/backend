from pydantic_settings import BaseSettings, SettingsConfigDict


class KeycloakSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KEYCLOAK_", env_file=".env", extra="ignore")

    # Browser-facing URL, token issuer is derived from it
    url: str = "http://localhost:8080"
    realm: str = "sheber"
    audience: str = "sheber-backend"
    swagger_client_id: str = "sheber-frontend"
    # Server-to-server URL for the Admin API (differs from `url` inside Docker)
    admin_url: str | None = None
    service_client_id: str = "sheber-backend"
    service_client_secret: str = ""

    @property
    def issuer(self) -> str:
        return f"{self.url.rstrip('/')}/realms/{self.realm}"

    @property
    def jwks_url(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/certs"

    @property
    def authorization_url(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/auth"

    @property
    def token_url(self) -> str:
        return f"{self.issuer}/protocol/openid-connect/token"

    @property
    def admin_base_url(self) -> str:
        return (self.admin_url or self.url).rstrip("/")
