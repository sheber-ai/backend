import uuid

import pytest
from httpx import AsyncClient

from tests.conftest import AuthHeaders

pytestmark = pytest.mark.db


async def test_get_my_profile_creates_profile(client: AsyncClient, auth_headers: AuthHeaders) -> None:
    user_id = uuid.uuid4()

    response = await client.get("/api/v1/users/me", headers=auth_headers(user_id, given_name="Айгерим"))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user_id)
    assert body["firstName"] == "Айгерим"
    assert body["onboarded"] is False
    assert body["workshopStatus"] is None


async def test_update_my_profile_normalizes_phone(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    headers = auth_headers(uuid.uuid4())

    response = await client.put(
        "/api/v1/users/me",
        headers=headers,
        json={"firstName": "Айгерим", "phone": "8 (701) 123-45-67", "cityId": str(cities["oskemen"])},
    )

    assert response.status_code == 200
    assert response.json()["phone"] == "+77011234567"
    assert response.json()["onboarded"] is True
    assert response.json()["city"] == {"id": str(cities["oskemen"]), "name": "Усть-Каменогорск"}


async def test_update_my_profile_rejects_invalid_phone(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    response = await client.put(
        "/api/v1/users/me",
        headers=auth_headers(uuid.uuid4()),
        json={"firstName": "Айгерим", "phone": "+1 202 555 0100 12", "cityId": str(cities["almaty"])},
    )

    assert response.status_code == 422


async def test_update_my_profile_rejects_hidden_city(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    response = await client.put(
        "/api/v1/users/me",
        headers=auth_headers(uuid.uuid4()),
        json={"firstName": "Айгерим", "phone": "87011234567", "cityId": str(cities["hidden"])},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "city_not_found"
