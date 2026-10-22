import time
from typing import Any, Protocol
from uuid import UUID

import httpx

from common.exceptions import ServiceUnavailableError
from enums.auth_enum import UserRoleEnum
from settings.keycloak_settings import KeycloakSettings


class RoleGranter(Protocol):
    async def grant_role(self, user_id: UUID, role: UserRoleEnum) -> None: ...

    async def revoke_role(self, user_id: UUID, role: UserRoleEnum) -> None: ...


class KeycloakAdminClient:
    """Realm role mapping through the Admin API, authenticated as the backend service account."""

    def __init__(self, settings: KeycloakSettings) -> None:
        self._settings = settings
        self._token: str | None = None
        self._token_expires_at = 0.0

    @property
    def _realm_url(self) -> str:
        return f"{self._settings.admin_base_url}/admin/realms/{self._settings.realm}"

    async def grant_role(self, user_id: UUID, role: UserRoleEnum) -> None:
        await self._map_role("POST", user_id, role)

    async def revoke_role(self, user_id: UUID, role: UserRoleEnum) -> None:
        await self._map_role("DELETE", user_id, role)

    async def _map_role(self, method: str, user_id: UUID, role: UserRoleEnum) -> None:
        async with httpx.AsyncClient(timeout=10) as http:
            try:
                headers = {"Authorization": f"Bearer {await self._access_token(http)}"}
                role_response = await http.get(f"{self._realm_url}/roles/{role.value}", headers=headers)
                role_response.raise_for_status()
                response = await http.request(
                    method,
                    f"{self._realm_url}/users/{user_id}/role-mappings/realm",
                    headers=headers,
                    json=[role_response.json()],
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise ServiceUnavailableError(f"Keycloak Admin API failed: {exc}") from exc

    async def _access_token(self, http: httpx.AsyncClient) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token
        response = await http.post(
            f"{self._settings.admin_base_url}/realms/{self._settings.realm}/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self._settings.service_client_id,
                "client_secret": self._settings.service_client_secret,
            },
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        self._token = str(payload["access_token"])
        self._token_expires_at = time.monotonic() + int(payload.get("expires_in", 60)) - 15
        return self._token
