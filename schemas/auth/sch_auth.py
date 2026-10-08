from typing import Any
from uuid import UUID

from enums.auth_enum import UserRoleEnum
from schemas.sch_base import BaseSchema


class CurrentUserSchema(BaseSchema):
    """User from the Keycloak access token. `id` is the token `sub`."""

    id: UUID
    email: str | None
    first_name: str | None
    last_name: str | None
    roles: list[UserRoleEnum]

    @classmethod
    def from_claims(cls, claims: dict[str, Any]) -> "CurrentUserSchema":
        known_roles = {role.value for role in UserRoleEnum}
        token_roles = claims.get("realm_access", {}).get("roles", [])
        return cls(
            id=claims["sub"],
            email=claims.get("email"),
            first_name=claims.get("given_name"),
            last_name=claims.get("family_name"),
            roles=[UserRoleEnum(role) for role in token_roles if role in known_roles],
        )

    def has_role(self, *roles: UserRoleEnum) -> bool:
        return any(role in self.roles for role in roles)
