import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import AuthHeaders, FakeRoleGranter
from tests.messages.test_messages import _published_order
from tests.orders.test_order_flow import CONTRACTOR_ROLES, _approved_workshop

pytestmark = pytest.mark.db


async def _kinds(client: AsyncClient, headers: dict[str, str]) -> list[str]:
    response = await client.get("/api/v1/notifications", headers=headers)
    return [item["kind"] for item in response.json()["items"]]


async def test_offer_lifecycle_notifies_both_sides(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner = auth_headers(uuid.uuid4())
    order_id = await _published_order(client, owner, cities["almaty"])
    first = await _approved_workshop(client, auth_headers, workshop_body, "Первая")
    second = await _approved_workshop(client, auth_headers, workshop_body, "Вторая")
    offer = await client.post(f"/api/v1/orders/{order_id}/offers", headers=first, json={"price": 300000, "days": 20})
    await client.post(f"/api/v1/orders/{order_id}/offers", headers=second, json={"price": 280000, "days": 25})

    await client.post(f"/api/v1/offers/{offer.json()['id']}/accept", headers=owner)
    await client.post(f"/api/v1/orders/{order_id}/start", headers=first)
    await client.post(f"/api/v1/orders/{order_id}/complete", headers=owner)

    owner_items = (await client.get("/api/v1/notifications", headers=owner)).json()["items"]
    assert [item["kind"] for item in owner_items] == ["order_started", "offer_received", "offer_received"]
    assert {item["actor"] for item in owner_items} == {"Первая", "Вторая"}
    assert all(item["orderId"] == order_id for item in owner_items)
    assert await _kinds(client, first) == ["order_completed", "offer_accepted", "workshop_approved"]
    assert await _kinds(client, second) == ["offer_rejected", "workshop_approved"]


async def test_cancel_notifies_pending_workshops(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner = auth_headers(uuid.uuid4())
    order_id = await _published_order(client, owner, cities["almaty"])
    workshop = await _approved_workshop(client, auth_headers, workshop_body, "Цех")
    await client.post(f"/api/v1/orders/{order_id}/offers", headers=workshop, json={"price": 300000, "days": 20})

    await client.post(f"/api/v1/orders/{order_id}/cancel", headers=owner)

    assert (await _kinds(client, workshop))[0] == "order_cancelled"


async def test_messages_coalesce_and_read_all(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner = auth_headers(uuid.uuid4())
    order_id = await _published_order(client, owner, cities["almaty"])
    workshop = await _approved_workshop(client, auth_headers, workshop_body, "Цех")
    for body in ("Здравствуйте", "Есть вопрос", "По размерам"):
        await client.post(f"/api/v1/orders/{order_id}/messages", headers=workshop, json={"body": body})

    assert await _kinds(client, owner) == ["message_received"]

    unread = await client.get("/api/v1/notifications", headers=owner, params={"unreadOnly": True})
    read = await client.post(f"/api/v1/notifications/{unread.json()['items'][0]['id']}/read", headers=owner)
    assert read.json()["readAt"] is not None
    assert (await client.get("/api/v1/notifications/summary", headers=owner)).json()["unread"] == 0

    await client.post(f"/api/v1/orders/{order_id}/messages", headers=workshop, json={"body": "Ещё"})
    assert (await client.get("/api/v1/notifications/summary", headers=owner)).json()["unread"] == 1
    await client.post("/api/v1/notifications/read-all", headers=owner)
    assert (await client.get("/api/v1/notifications/summary", headers=owner)).json()["unread"] == 0


async def test_cannot_read_foreign_notification(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner = auth_headers(uuid.uuid4())
    order_id = await _published_order(client, owner, cities["almaty"])
    workshop = await _approved_workshop(client, auth_headers, workshop_body, "Цех")
    await client.post(f"/api/v1/orders/{order_id}/messages", headers=workshop, json={"body": "Здравствуйте"})
    notification_id = (await client.get("/api/v1/notifications", headers=owner)).json()["items"][0]["id"]

    response = await client.post(f"/api/v1/notifications/{notification_id}/read", headers=workshop)

    assert response.status_code == 404


async def test_new_order_notifies_matching_workshops(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    oskemen = {**workshop_body, "cityId": str(cities["oskemen"])}
    local = await _approved_workshop(client, auth_headers, workshop_body, "Местная")
    serves = await _approved_workshop(
        client, auth_headers, {**oskemen, "serviceCityIds": [str(cities["almaty"])]}, "Выездная"
    )
    elsewhere = await _approved_workshop(client, auth_headers, oskemen, "Далёкая")
    shelving = {**workshop_body, "furnitureTypes": ["shelving"]}
    other_type = await _approved_workshop(client, auth_headers, shelving, "Стеллажи")
    pending = auth_headers(uuid.uuid4(), roles=CONTRACTOR_ROLES)
    await client.put("/api/v1/workshops/mine", headers=pending, json=workshop_body)

    owner = auth_headers(uuid.uuid4())
    order_id = await _published_order(client, owner, cities["almaty"])

    for headers in (local, serves):
        items = (await client.get("/api/v1/notifications", headers=headers)).json()["items"]
        assert items[0]["kind"] == "new_order"
        assert items[0]["orderId"] == order_id
        assert items[0]["subject"] == "Шкаф в спальню"
    for headers in (elsewhere, other_type, pending):
        assert "new_order" not in await _kinds(client, headers)
    assert await _kinds(client, owner) == []
