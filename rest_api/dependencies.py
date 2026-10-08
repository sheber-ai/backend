import functools
from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2AuthorizationCodeBearer

from common.exceptions import PermissionDeniedError, UnauthorizedError
from common.security.keycloak import KeycloakTokenVerifier
from enums.auth_enum import UserRoleEnum
from schemas.auth.sch_auth import CurrentUserSchema
from settings.keycloak_settings import KeycloakSettings
from settings.resolver import get_settings

_keycloak_settings = get_settings(KeycloakSettings)

# Documents Keycloak login in OpenAPI (Swagger "Authorize"); the token comes as a Bearer header.
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=_keycloak_settings.authorization_url,
    tokenUrl=_keycloak_settings.token_url,
    scheme_name="keycloak",
    auto_error=False,
)


@functools.cache
def get_token_verifier() -> KeycloakTokenVerifier:
    return KeycloakTokenVerifier(get_settings(KeycloakSettings))


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    verifier: Annotated[KeycloakTokenVerifier, Depends(get_token_verifier)],
) -> CurrentUserSchema:
    if not token:
        raise UnauthorizedError("Authentication required")
    claims = await verifier.verify(token)
    return CurrentUserSchema.from_claims(claims)


CurrentUser = Annotated[CurrentUserSchema, Depends(get_current_user)]


def require_roles(*roles: UserRoleEnum) -> Callable[[CurrentUserSchema], Awaitable[CurrentUserSchema]]:
    """Allow users with any of the given roles."""

    async def dependency(user: CurrentUser) -> CurrentUserSchema:
        if not user.has_role(*roles):
            raise PermissionDeniedError("Not enough permissions")
        return user

    return dependency


ContractorUser = Annotated[CurrentUserSchema, Depends(require_roles(UserRoleEnum.CONTRACTOR))]
AdminUser = Annotated[CurrentUserSchema, Depends(require_roles(UserRoleEnum.ADMIN))]
