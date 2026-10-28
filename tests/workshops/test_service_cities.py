import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import AuthHeaders, FakeRoleGranter
from tests.orders.test_order_flow import CONTRACTOR_ROLES, _approved_workshop, _client_with_design

pytestmark = pytest.mark.db


async def test_workshop_saves_extra_cities_without_repeats(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID], workshop_body: dict[str, Any]
) -> None:
    headers = auth_headers(uuid.uuid4(), roles=CONTRACTOR_ROLES)
    oskemen, almaty = str(cities["oskemen"]), str(cities["almaty"])

    saved = await client.put(
        "/api/v1/workshops/mine",
        headers=headers,
        json={**workshop_body, "serviceCityIds": [oskemen, almaty, oskemen]},
    )
    again = await client.get("/api/v1/workshops/mine", headers=headers)

    assert saved.status_code == 200, saved.text
    # The main city (Almaty) is not repeated among the extra ones
    assert saved.json()["serviceCities"] == [{"id": oskemen, "name": "Усть-Каменогорск"}]
    assert again.json()["serviceCities"] == saved.json()["serviceCities"]

    cleared = await client.put("/api/v1/workshops/mine", headers=headers, json={**workshop_body, "serviceCityIds": []})
    assert cleared.json()["serviceCities"] == []


async def test_workshop_rejects_unknown_or_hidden_cities(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID], workshop_body: dict[str, Any]
) -> None:
    headers = auth_headers(uuid.uuid4(), roles=CONTRACTOR_ROLES)
    for city_id in (cities["hidden"], uuid.uuid4()):
        response = await client.put(
            "/api/v1/workshops/mine", headers=headers, json={**workshop_body, "serviceCityIds": [str(city_id)]}
        )
        assert response.json()["code"] == "city_not_found"
    assert (await client.get("/api/v1/workshops/mine", headers=headers)).status_code == 404


async def test_old_clients_keep_working_without_the_field(
    client: AsyncClient, auth_headers: AuthHeaders, workshop_body: dict[str, Any]
) -> None:
    response = await client.put(
        "/api/v1/workshops/mine", headers=auth_headers(uuid.uuid4(), roles=CONTRACTOR_ROLES), json=workshop_body
    )
    assert response.status_code == 200
    assert response.json()["serviceCities"] == []


async def test_feed_shows_orders_from_every_served_city(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    almaty_client = auth_headers(uuid.uuid4())
    oskemen_client = auth_headers(uuid.uuid4())
    orders = {}
    for headers, slug in ((almaty_client, "almaty"), (oskemen_client, "oskemen")):
        design_id = await _client_with_design(client, headers, cities[slug])
        created = await client.post(
            "/api/v1/orders", headers=headers, json={"designId": design_id, "cityId": str(cities[slug])}
        )
        orders[slug] = created.json()["id"]

    local = await _approved_workshop(client, auth_headers, workshop_body, "Только Алматы")
    wide = await _approved_workshop(
        client, auth_headers, {**workshop_body, "serviceCityIds": [str(cities["oskemen"])]}, "Два города"
    )

    async def feed(headers: dict[str, str], **params: Any) -> set[str]:
        response = await client.get("/api/v1/orders/feed", headers=headers, params=params)
        return {item["id"] for item in response.json()["items"]}

    assert await feed(local, myCities=True) == {orders["almaty"]}
    assert await feed(wide, myCities=True) == {orders["almaty"], orders["oskemen"]}
    assert await feed(wide, myCities=True, cityId=str(cities["oskemen"])) == {orders["oskemen"]}
    # Without the flag the feed is not limited, as before
    assert await feed(local) == {orders["almaty"], orders["oskemen"]}

    public = await client.get(
        f"/api/v1/workshops/{(await client.get('/api/v1/workshops/mine', headers=wide)).json()['id']}"
    )
    assert [city["name"] for city in public.json()["serviceCities"]] == ["Усть-Каменогорск"]
