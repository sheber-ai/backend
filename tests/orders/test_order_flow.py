import uuid
from datetime import date, timedelta
from typing import Any

import pytest
from httpx import AsyncClient

from enums.auth_enum import UserRoleEnum
from tests.conftest import AuthHeaders, FakeRoleGranter
from tests.samples import WARDROBE_DOCUMENT

pytestmark = pytest.mark.db

CONTRACTOR_ROLES = (UserRoleEnum.CLIENT, UserRoleEnum.CONTRACTOR)


async def _client_with_design(client: AsyncClient, headers: dict[str, str], city_id: uuid.UUID) -> str:
    await client.put(
        "/api/v1/users/me",
        headers=headers,
        json={"firstName": "Айгерим", "phone": "87011112233", "cityId": str(city_id)},
    )
    design = await client.post(
        "/api/v1/designs",
        headers=headers,
        json={"title": "Шкаф в спальню", "furnitureType": "wardrobe", "document": WARDROBE_DOCUMENT},
    )
    assert design.status_code == 201, design.text
    return str(design.json()["id"])


async def _approved_workshop(
    client: AsyncClient, auth_headers: AuthHeaders, body: dict[str, Any], name: str
) -> dict[str, str]:
    owner_id = uuid.uuid4()
    headers = auth_headers(owner_id, roles=CONTRACTOR_ROLES)
    workshop = await client.put("/api/v1/workshops/mine", headers=headers, json={**body, "name": name})
    admin = auth_headers(uuid.uuid4(), roles=(UserRoleEnum.ADMIN,))
    await client.post(f"/api/v1/workshops/{workshop.json()['id']}/approve", headers=admin)
    return headers


async def test_order_flow_from_publish_to_completion(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner = auth_headers(uuid.uuid4())
    almaty = str(cities["almaty"])
    design_id = await _client_with_design(client, owner, cities["almaty"])
    first = await _approved_workshop(client, auth_headers, workshop_body, "Первая мастерская")
    second = await _approved_workshop(client, auth_headers, workshop_body, "Вторая мастерская")

    created = await client.post(
        "/api/v1/orders",
        headers=owner,
        json={
            "designId": design_id,
            "cityId": almaty,
            "budget": 450000,
            "deadline": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["id"]
    assert created.json()["document"] == WARDROBE_DOCUMENT
    assert created.json()["contact"] is None
    assert created.json()["city"] == {"id": almaty, "name": "Алматы"}

    feed = await client.get("/api/v1/orders/feed", headers=first, params={"cityId": almaty})
    assert [item["id"] for item in feed.json()["items"]] == [order_id]
    assert feed.json()["items"][0]["myOfferStatus"] is None

    offer = await client.post(
        f"/api/v1/orders/{order_id}/offers", headers=first, json={"price": 420000, "days": 21, "comment": "ЛДСП Egger"}
    )
    duplicate = await client.post(f"/api/v1/orders/{order_id}/offers", headers=first, json={"price": 1000, "days": 1})
    await client.post(f"/api/v1/orders/{order_id}/offers", headers=second, json={"price": 390000, "days": 30})
    assert offer.status_code == 201
    assert duplicate.json()["code"] == "offer_exists"

    offers = await client.get(f"/api/v1/orders/{order_id}/offers", headers=owner)
    assert offers.json()["total"] == 2
    assert offers.json()["items"][0]["workshop"]["name"] == "Первая мастерская"

    accepted = await client.post(f"/api/v1/offers/{offer.json()['id']}/accept", headers=owner)
    assert accepted.json()["status"] == "accepted"

    for_owner = await client.get(f"/api/v1/orders/{order_id}", headers=owner)
    for_workshop = await client.get(f"/api/v1/orders/{order_id}", headers=first)
    second_offers = await client.get("/api/v1/offers/mine", headers=second)
    assert for_owner.json()["status"] == "assigned"
    assert for_owner.json()["contact"]["name"] == "Первая мастерская"
    assert for_workshop.json()["contact"]["name"] == "Айгерим"
    assert for_workshop.json()["contact"]["phone"] == "+77011112233"
    assert second_offers.json()["items"][0]["status"] == "rejected"

    started = await client.post(f"/api/v1/orders/{order_id}/start", headers=first)
    completed = await client.post(f"/api/v1/orders/{order_id}/complete", headers=owner)
    assert started.json()["status"] == "in_progress"
    assert completed.json()["status"] == "completed"


async def test_order_requires_phone(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    owner = auth_headers(uuid.uuid4())
    design = await client.post(
        "/api/v1/designs",
        headers=owner,
        json={"title": "Комод", "furnitureType": "dresser", "document": WARDROBE_DOCUMENT},
    )

    response = await client.post(
        "/api/v1/orders", headers=owner, json={"designId": design.json()["id"], "cityId": str(cities["almaty"])}
    )

    assert response.json()["code"] == "profile_incomplete"


async def test_feed_requires_approved_workshop(client: AsyncClient, auth_headers: AuthHeaders) -> None:
    contractor = auth_headers(uuid.uuid4(), roles=CONTRACTOR_ROLES)

    response = await client.get("/api/v1/orders/feed", headers=contractor)

    assert response.status_code == 403
    assert response.json()["code"] == "workshop_required"


async def test_other_client_cannot_see_order(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    owner = auth_headers(uuid.uuid4())
    design_id = await _client_with_design(client, owner, cities["almaty"])
    body = {"designId": design_id, "cityId": str(cities["almaty"])}
    order = await client.post("/api/v1/orders", headers=owner, json=body)

    response = await client.get(f"/api/v1/orders/{order.json()['id']}", headers=auth_headers(uuid.uuid4()))

    assert response.status_code == 403


async def test_other_client_cannot_read_design(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    design_id = await _client_with_design(client, auth_headers(uuid.uuid4()), cities["almaty"])

    response = await client.get(f"/api/v1/designs/{design_id}", headers=auth_headers(uuid.uuid4()))

    assert response.status_code == 403
