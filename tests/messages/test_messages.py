import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from tests.conftest import AuthHeaders, FakeRoleGranter
from tests.orders.test_order_flow import _approved_workshop, _client_with_design

pytestmark = pytest.mark.db


async def _published_order(client: AsyncClient, owner: dict[str, str], city_id: uuid.UUID) -> str:
    design_id = await _client_with_design(client, owner, city_id)
    order = await client.post("/api/v1/orders", headers=owner, json={"designId": design_id, "cityId": str(city_id)})
    assert order.status_code == 201, order.text
    return str(order.json()["id"])


async def _workshop_id(client: AsyncClient, headers: dict[str, str]) -> str:
    return str((await client.get("/api/v1/workshops/mine", headers=headers)).json()["id"])


async def test_workshop_asks_and_client_answers(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner = auth_headers(uuid.uuid4())
    order_id = await _published_order(client, owner, cities["almaty"])
    workshop = await _approved_workshop(client, auth_headers, workshop_body, "Мастерская")
    workshop_id = await _workshop_id(client, workshop)

    question = await client.post(
        f"/api/v1/orders/{order_id}/messages", headers=workshop, json={"body": "  Какая глубина ниши?  "}
    )
    assert question.status_code == 201, question.text
    assert question.json()["body"] == "Какая глубина ниши?"
    assert question.json()["author"] == "workshop"
    assert question.json()["isMine"] is True

    threads = await client.get(f"/api/v1/orders/{order_id}/threads", headers=owner)
    assert threads.json()["total"] == 1
    assert threads.json()["items"][0]["workshop"]["id"] == workshop_id
    assert threads.json()["items"][0]["unreadCount"] == 1
    assert threads.json()["items"][0]["offerStatus"] is None

    summary = await client.get("/api/v1/notifications/summary", headers=owner)
    assert summary.json()["unread"] == 1

    thread = await client.get(f"/api/v1/orders/{order_id}/messages", headers=owner, params={"workshopId": workshop_id})
    assert thread.json()["canWrite"] is True
    assert [m["isMine"] for m in thread.json()["messages"]] == [False]

    answer = await client.post(
        f"/api/v1/orders/{order_id}/messages", headers=owner, json={"body": "600 мм", "workshopId": workshop_id}
    )
    assert answer.status_code == 201
    assert answer.json()["author"] == "client"

    after = await client.get(f"/api/v1/orders/{order_id}/threads", headers=owner)
    assert after.json()["items"][0]["unreadCount"] == 0
    assert (await client.get("/api/v1/notifications/summary", headers=owner)).json()["unread"] == 0

    for_workshop = await client.get(f"/api/v1/orders/{order_id}/messages", headers=workshop)
    assert [m["body"] for m in for_workshop.json()["messages"]] == ["Какая глубина ниши?", "600 мм"]
    assert for_workshop.json()["messages"][0]["readAt"] is not None


async def test_owner_must_choose_thread(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    owner = auth_headers(uuid.uuid4())
    order_id = await _published_order(client, owner, cities["almaty"])

    response = await client.post(f"/api/v1/orders/{order_id}/messages", headers=owner, json={"body": "Привет"})

    assert response.json()["code"] == "thread_required"


async def test_owner_cannot_write_to_uninvolved_workshop(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner = auth_headers(uuid.uuid4())
    order_id = await _published_order(client, owner, cities["almaty"])
    workshop_id = await _workshop_id(client, await _approved_workshop(client, auth_headers, workshop_body, "Цех"))

    response = await client.post(
        f"/api/v1/orders/{order_id}/messages", headers=owner, json={"body": "Привет", "workshopId": workshop_id}
    )

    assert response.status_code == 403


async def test_strangers_cannot_read_thread(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    owner = auth_headers(uuid.uuid4())
    order_id = await _published_order(client, owner, cities["almaty"])

    response = await client.get(f"/api/v1/orders/{order_id}/messages", headers=auth_headers(uuid.uuid4()))

    assert response.status_code == 403
    assert response.json()["code"] == "workshop_required"


async def test_thread_closes_for_workshops_not_chosen(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner = auth_headers(uuid.uuid4())
    order_id = await _published_order(client, owner, cities["almaty"])
    chosen = await _approved_workshop(client, auth_headers, workshop_body, "Выбранная")
    other = await _approved_workshop(client, auth_headers, workshop_body, "Другая")
    offer = await client.post(f"/api/v1/orders/{order_id}/offers", headers=chosen, json={"price": 300000, "days": 20})
    await client.post(f"/api/v1/orders/{order_id}/messages", headers=other, json={"body": "Можно уточнить?"})
    await client.post(f"/api/v1/offers/{offer.json()['id']}/accept", headers=owner)

    closed = await client.post(f"/api/v1/orders/{order_id}/messages", headers=other, json={"body": "Ещё вопрос"})
    open_ = await client.post(f"/api/v1/orders/{order_id}/messages", headers=chosen, json={"body": "Начинаем"})
    threads = await client.get(f"/api/v1/orders/{order_id}/threads", headers=owner)

    assert closed.json()["code"] == "invalid_status"
    assert open_.status_code == 201
    by_name = {item["workshop"]["name"]: item for item in threads.json()["items"]}
    assert by_name["Выбранная"]["canWrite"] is True
    assert by_name["Выбранная"]["offerStatus"] == "accepted"
    assert by_name["Другая"]["canWrite"] is False
