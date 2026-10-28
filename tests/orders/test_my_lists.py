import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import AuthHeaders, FakeRoleGranter
from tests.orders.test_order_flow import _approved_workshop, _client_with_design
from tests.samples import WARDROBE_DOCUMENT

pytestmark = pytest.mark.db


async def _publish(client: AsyncClient, headers: dict[str, str], city_id: uuid.UUID, title: str) -> str:
    design = await client.post(
        "/api/v1/designs",
        headers=headers,
        json={"title": title, "furnitureType": "wardrobe", "document": WARDROBE_DOCUMENT},
    )
    order = await client.post(
        "/api/v1/orders", headers=headers, json={"designId": design.json()["id"], "cityId": str(city_id)}
    )
    assert order.status_code == 201, order.text
    return str(order.json()["id"])


async def test_my_orders_filter_by_tab_and_page_without_repeats(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    owner = auth_headers(uuid.uuid4())
    await _client_with_design(client, owner, cities["almaty"])
    ids = [await _publish(client, owner, cities["almaty"], f"Шкаф {index}") for index in range(5)]
    await client.post(f"/api/v1/orders/{ids[0]}/cancel", headers=owner)

    pages = [
        (
            await client.get(
                "/api/v1/orders/mine", headers=owner, params={"group": "active", "offset": offset, "limit": 2}
            )
        )
        for offset in (0, 2, 4)
    ]
    seen = [item["id"] for page in pages for item in page.json()["items"]]
    assert all(page.json()["total"] == 4 for page in pages)
    assert len(seen) == 4
    assert set(seen) == set(ids[1:])
    assert pages[0].json()["counts"] == {"active": 4, "completed": 0, "cancelled": 1}

    cancelled = await client.get("/api/v1/orders/mine", headers=owner, params={"group": "cancelled"})
    everything = await client.get("/api/v1/orders/mine", headers=owner)
    empty = await client.get("/api/v1/orders/mine", headers=owner, params={"group": "completed"})
    assert [item["id"] for item in cancelled.json()["items"]] == [ids[0]]
    assert everything.json()["total"] == 5
    assert empty.json() == {"items": [], "total": 0, "counts": {"active": 4, "completed": 0, "cancelled": 1}}


async def test_my_orders_rejects_unknown_tab(client: AsyncClient, auth_headers: AuthHeaders) -> None:
    response = await client.get("/api/v1/orders/mine", headers=auth_headers(uuid.uuid4()), params={"group": "x"})
    assert response.status_code == 422


async def test_my_offers_split_into_active_and_archive(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner = auth_headers(uuid.uuid4())
    await _client_with_design(client, owner, cities["almaty"])
    workshop = await _approved_workshop(client, auth_headers, workshop_body, "Мастерская")
    waiting, cancelled, chosen = [await _publish(client, owner, cities["almaty"], f"Шкаф {i}") for i in range(3)]
    offer_ids = {}
    for order_id in (waiting, cancelled, chosen):
        offer = await client.post(
            f"/api/v1/orders/{order_id}/offers", headers=workshop, json={"price": 100000, "days": 10}
        )
        assert offer.status_code == 201, offer.text
        offer_ids[order_id] = offer.json()["id"]
    await client.post(f"/api/v1/orders/{cancelled}/cancel", headers=owner)
    await client.post(f"/api/v1/offers/{offer_ids[chosen]}/accept", headers=owner)

    active = await client.get("/api/v1/offers/mine", headers=workshop, params={"tab": "active"})
    archive = await client.get("/api/v1/offers/mine", headers=workshop, params={"tab": "archive"})
    second_page = await client.get(
        "/api/v1/offers/mine", headers=workshop, params={"tab": "active", "offset": 1, "limit": 1}
    )

    assert {item["order"]["id"] for item in active.json()["items"]} == {waiting, chosen}
    assert [item["order"]["id"] for item in archive.json()["items"]] == [cancelled]
    assert active.json()["counts"] == {"active": 2, "archive": 1}
    assert second_page.json()["total"] == 2
    assert len(second_page.json()["items"]) == 1
    assert second_page.json()["items"][0]["id"] != active.json()["items"][0]["id"]

    await client.post(f"/api/v1/orders/{chosen}/complete", headers=owner)
    after = await client.get("/api/v1/offers/mine", headers=workshop, params={"tab": "archive"})
    assert after.json()["counts"] == {"active": 1, "archive": 2}
