import asyncio
from typing import Any, Protocol

import jwt

from common.exceptions import ServiceUnavailableError, UnauthorizedError
from settings.keycloak_settings import KeycloakSettings

type TokenClaims = dict[str, Any]


class SigningKeyResolver(Protocol):
    def get_signing_key_from_jwt(self, token: str) -> jwt.PyJWK: ...


class KeycloakTokenVerifier:
    """Verifies Keycloak access tokens locally against the cached realm JWKS."""

    def __init__(self, settings: KeycloakSettings, key_resolver: SigningKeyResolver | None = None) -> None:
        self._settings = settings
        self._key_resolver = key_resolver or jwt.PyJWKClient(settings.jwks_url, cache_keys=True, lifespan=3600)

    async def verify(self, token: str) -> TokenClaims:
        try:
            # PyJWKClient does blocking I/O
            signing_key = await asyncio.to_thread(self._key_resolver.get_signing_key_from_jwt, token)
        except jwt.PyJWKClientConnectionError as exc:
            raise ServiceUnavailableError("Keycloak is unavailable") from exc
        except (jwt.PyJWKClientError, jwt.DecodeError) as exc:
            raise UnauthorizedError("Invalid token") from exc

        try:
            claims: TokenClaims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self._settings.audience,
                issuer=self._settings.issuer,
                options={"require": ["exp", "iat", "sub"]},
                leeway=10,
            )
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError("Token expired") from exc
        except jwt.InvalidTokenError as exc:
            raise UnauthorizedError("Invalid token") from exc
        return claims
