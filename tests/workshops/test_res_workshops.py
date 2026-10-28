import uuid
from typing import Any

import pytest
from httpx import AsyncClient

from enums.auth_enum import UserRoleEnum
from tests.conftest import AuthHeaders, FakeRoleGranter

pytestmark = pytest.mark.db


async def test_workshop_application_is_pending(
    client: AsyncClient, auth_headers: AuthHeaders, workshop_body: dict[str, Any]
) -> None:
    headers = auth_headers(uuid.uuid4())

    response = await client.put("/api/v1/workshops/mine", headers=headers, json=workshop_body)

    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    profile = await client.get("/api/v1/users/me", headers=headers)
    assert profile.json()["workshopStatus"] == "pending"


async def test_pending_workshop_is_not_public(
    client: AsyncClient, auth_headers: AuthHeaders, workshop_body: dict[str, Any]
) -> None:
    workshop = await client.put("/api/v1/workshops/mine", headers=auth_headers(uuid.uuid4()), json=workshop_body)

    response = await client.get(f"/api/v1/workshops/{workshop.json()['id']}")

    assert response.status_code == 404


async def test_approve_workshop_grants_contractor_role(
    client: AsyncClient, auth_headers: AuthHeaders, role_granter: FakeRoleGranter, workshop_body: dict[str, Any]
) -> None:
    owner_id = uuid.uuid4()
    workshop = await client.put("/api/v1/workshops/mine", headers=auth_headers(owner_id), json=workshop_body)
    admin = auth_headers(uuid.uuid4(), roles=(UserRoleEnum.CLIENT, UserRoleEnum.ADMIN))

    pending = await client.get("/api/v1/workshops", headers=admin, params={"status": "pending"})
    response = await client.post(f"/api/v1/workshops/{workshop.json()['id']}/approve", headers=admin)

    assert [item["id"] for item in pending.json()["items"]] == [workshop.json()["id"]]
    assert response.json()["status"] == "approved"
    assert role_granter.calls == [("grant", owner_id, UserRoleEnum.CONTRACTOR)]


async def test_rejected_workshop_returns_to_review_after_edit(
    client: AsyncClient, auth_headers: AuthHeaders, role_granter: FakeRoleGranter, workshop_body: dict[str, Any]
) -> None:
    owner = auth_headers(uuid.uuid4())
    admin = auth_headers(uuid.uuid4(), roles=(UserRoleEnum.ADMIN,))
    workshop = await client.put("/api/v1/workshops/mine", headers=owner, json=workshop_body)

    await client.post(
        f"/api/v1/workshops/{workshop.json()['id']}/reject", headers=admin, json={"reason": "Нет портфолио"}
    )
    rejected = await client.get("/api/v1/workshops/mine", headers=owner)
    resubmitted = await client.put("/api/v1/workshops/mine", headers=owner, json=workshop_body)

    assert rejected.json()["rejectionReason"] == "Нет портфолио"
    assert resubmitted.json()["status"] == "pending"
    assert role_granter.calls == []


async def test_list_workshops_requires_admin(client: AsyncClient, auth_headers: AuthHeaders) -> None:
    response = await client.get("/api/v1/workshops", headers=auth_headers(uuid.uuid4()))

    assert response.status_code == 403


async def test_workshop_city_is_localized(
    client: AsyncClient, auth_headers: AuthHeaders, workshop_body: dict[str, Any]
) -> None:
    headers = auth_headers(uuid.uuid4())
    await client.put("/api/v1/workshops/mine", headers=headers, json=workshop_body)

    response = await client.get("/api/v1/workshops/mine", headers={**headers, "Accept-Language": "en-US,en;q=0.9"})

    assert response.json()["city"]["name"] == "Almaty"


async def test_public_profile_shows_services_and_real_figures(
    client: AsyncClient, auth_headers: AuthHeaders, role_granter: FakeRoleGranter, workshop_body: dict[str, Any]
) -> None:
    owner = auth_headers(uuid.uuid4())
    body = {
        **workshop_body,
        "services": ["measurement", "installation", "measurement"],
        "materials": ["chipboard", "mdf"],
        "warrantyMonths": 24,
        "foundedYear": 2015,
    }
    workshop = await client.put("/api/v1/workshops/mine", headers=owner, json=body)
    await client.post(
        f"/api/v1/workshops/{workshop.json()['id']}/approve",
        headers=auth_headers(uuid.uuid4(), roles=(UserRoleEnum.ADMIN,)),
    )

    response = await client.get(f"/api/v1/workshops/{workshop.json()['id']}")

    profile = response.json()
    assert profile["services"] == ["measurement", "installation"]
    assert profile["materials"] == ["chipboard", "mdf"]
    assert profile["warrantyMonths"] == 24
    assert profile["foundedYear"] == 2015
    assert profile["completedOrders"] == 0
    assert profile["verifiedAt"] is not None
    assert "phone" not in profile
    assert "taxId" not in profile


async def test_founded_year_cannot_be_in_future(
    client: AsyncClient, auth_headers: AuthHeaders, workshop_body: dict[str, Any]
) -> None:
    response = await client.put(
        "/api/v1/workshops/mine", headers=auth_headers(uuid.uuid4()), json={**workshop_body, "foundedYear": 2999}
    )

    assert response.status_code == 422
