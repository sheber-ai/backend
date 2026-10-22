from fastapi import FastAPI
from httpx import AsyncClient

from tests.conftest import USER_ID, MakeToken


async def test_get_me_returns_user_from_token(auth_app: FastAPI, client: AsyncClient, make_token: MakeToken) -> None:
    response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {make_token()}"})

    assert response.status_code == 200
    assert response.json() == {
        "id": USER_ID,
        "email": "client@sheber.local",
        "firstName": "Айгерим",
        "lastName": "Клиентова",
        "roles": ["client"],
    }


async def test_get_me_without_token_is_unauthorized(auth_app: FastAPI, client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"
