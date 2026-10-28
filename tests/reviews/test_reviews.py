import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from enums.auth_enum import UserRoleEnum
from tests.conftest import AuthHeaders, FakeRoleGranter
from tests.messages.test_messages import _published_order
from tests.orders.test_order_flow import _approved_workshop

pytestmark = pytest.mark.db


async def _completed_order(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID], workshop_body: dict[str, Any]
) -> tuple[dict[str, str], dict[str, str], str, str]:
    owner = auth_headers(uuid.uuid4(), given_name="Айгерим", family_name="Клиентова")
    order_id = await _published_order(client, owner, cities["almaty"])
    workshop = await _approved_workshop(client, auth_headers, workshop_body, "Цех")
    workshop_id = (await client.get("/api/v1/workshops/mine", headers=workshop)).json()["id"]
    offer = await client.post(f"/api/v1/orders/{order_id}/offers", headers=workshop, json={"price": 300000, "days": 20})
    await client.post(f"/api/v1/offers/{offer.json()['id']}/accept", headers=owner)
    await client.post(f"/api/v1/orders/{order_id}/complete", headers=owner)
    return owner, workshop, order_id, workshop_id


async def test_client_reviews_the_workshop_after_completion(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner, workshop, order_id, workshop_id = await _completed_order(client, auth_headers, cities, workshop_body)

    created = await client.put(
        f"/api/v1/orders/{order_id}/review", headers=owner, json={"rating": 4, "text": "  Аккуратно, в срок  "}
    )
    corrected = await client.put(f"/api/v1/orders/{order_id}/review", headers=owner, json={"rating": 5})
    public = await client.get(f"/api/v1/workshops/{workshop_id}/reviews")
    profile = await client.get(f"/api/v1/workshops/{workshop_id}")
    seen_by_workshop = await client.get(f"/api/v1/orders/{order_id}/review", headers=workshop)
    notifications = await client.get("/api/v1/notifications", headers=workshop)

    assert created.status_code == 200, created.text
    assert created.json()["text"] == "Аккуратно, в срок"
    # The profile here has no last name; the initial rule is covered below
    assert created.json()["author"] == "Айгерим"
    assert corrected.json()["id"] == created.json()["id"]
    assert public.json()["total"] == 1
    assert public.json()["items"][0]["rating"] == 5
    assert (profile.json()["reviewsCount"], profile.json()["ratingAverage"]) == (1, 5.0)
    assert seen_by_workshop.json()["rating"] == 5
    assert notifications.json()["items"][0]["kind"] == "review_received"


async def test_review_needs_a_completed_order_of_your_own(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner = auth_headers(uuid.uuid4())
    open_order = await _published_order(client, owner, cities["almaty"])
    _, workshop, done_order, _ = await _completed_order(client, auth_headers, cities, workshop_body)
    stranger = auth_headers(uuid.uuid4())

    too_early = await client.put(f"/api/v1/orders/{open_order}/review", headers=owner, json={"rating": 5})
    by_stranger = await client.put(f"/api/v1/orders/{done_order}/review", headers=stranger, json={"rating": 1})
    by_workshop = await client.put(f"/api/v1/orders/{done_order}/review", headers=workshop, json={"rating": 5})
    out_of_range = await client.put(f"/api/v1/orders/{done_order}/review", headers=owner, json={"rating": 6})
    stranger_reads = await client.get(f"/api/v1/orders/{done_order}/review", headers=stranger)

    assert too_early.json()["code"] == "review_not_allowed"
    assert by_stranger.status_code == 403
    assert by_workshop.status_code == 403
    assert out_of_range.status_code == 422
    assert stranger_reads.status_code == 403


async def test_profile_without_reviews_has_no_rating(
    client: AsyncClient, auth_headers: AuthHeaders, role_granter: FakeRoleGranter, workshop_body: dict[str, Any]
) -> None:
    owner = auth_headers(uuid.uuid4())
    workshop = await client.put("/api/v1/workshops/mine", headers=owner, json=workshop_body)
    await client.post(
        f"/api/v1/workshops/{workshop.json()['id']}/approve",
        headers=auth_headers(uuid.uuid4(), roles=(UserRoleEnum.ADMIN,)),
    )

    profile = await client.get(f"/api/v1/workshops/{workshop.json()['id']}")

    assert (profile.json()["reviewsCount"], profile.json()["ratingAverage"]) == (0, None)


def test_author_shows_first_name_and_initial_only() -> None:
    from models.users.mdl_user import User
    from services.reviews.svc_reviews import review_author

    assert review_author(User(first_name="Айгерим", last_name="Клиентова")) == "Айгерим К."
    assert review_author(User(first_name=None, last_name="Клиентова", email="a@b.kz")) == ""


async def test_workshop_replies_to_its_review(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner, workshop, order_id, workshop_id = await _completed_order(client, auth_headers, cities, workshop_body)
    url = f"/api/v1/orders/{order_id}/review/reply"

    early = await client.put(url, headers=workshop, json={"text": "Спасибо!"})
    await client.put(f"/api/v1/orders/{order_id}/review", headers=owner, json={"rating": 5, "text": "Отлично"})
    blank = await client.put(url, headers=workshop, json={"text": "   "})
    stranger = await _approved_workshop(client, auth_headers, workshop_body, "Чужой")
    foreign = await client.put(url, headers=stranger, json={"text": "Спасибо!"})
    by_client = await client.put(url, headers=owner, json={"text": "Спасибо!"})
    first = await client.put(url, headers=workshop, json={"text": "  Спасибо, рады были помочь  "})
    edited = await client.put(url, headers=workshop, json={"text": "Спасибо за заказ!"})
    public = await client.get(f"/api/v1/workshops/{workshop_id}/reviews")

    assert early.status_code == 403
    assert blank.status_code == 422
    assert foreign.status_code == 403
    assert by_client.status_code == 403
    assert first.status_code == 200, first.text
    assert first.json()["reply"] == "Спасибо, рады были помочь"
    assert first.json()["repliedAt"] is not None
    assert edited.json()["reply"] == "Спасибо за заказ!"
    assert public.json()["items"][0]["reply"] == "Спасибо за заказ!"
    owner_kinds = [item["kind"] for item in (await client.get("/api/v1/notifications", headers=owner)).json()["items"]]
    assert owner_kinds.count("review_replied") == 1
