import io
import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from PIL import Image

from enums.auth_enum import UserRoleEnum
from tests.conftest import AuthHeaders, FakeRoleGranter
from tests.messages.test_messages import _published_order
from tests.orders.test_order_flow import _approved_workshop, _client_with_design

pytestmark = pytest.mark.db

URL = "/api/v1/attachments"


def image_bytes(fmt: str = "PNG", size: tuple[int, int] = (40, 30), exif: bytes | None = None) -> bytes:
    out = io.BytesIO()
    image = Image.new("RGB", size, (180, 120, 60))
    if exif is not None:
        image.save(out, fmt, exif=exif)
    else:
        image.save(out, fmt)
    return out.getvalue()


async def upload(
    client: AsyncClient,
    headers: dict[str, str],
    purpose: str,
    data: bytes,
    name: str = "photo.png",
    **target: str,
) -> Any:
    form = {"purpose": purpose, **target}
    return await client.post(URL, headers=headers, data=form, files={"file": (name, data, "image/png")})


async def content(client: AsyncClient, url: str) -> Any:
    return await client.get(url.removeprefix("http://localhost:8000"))


async def test_upload_stores_safe_metadata_and_serves_the_file(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    owner = auth_headers(uuid.uuid4())
    design_id = await _client_with_design(client, owner, cities["almaty"])

    response = await upload(client, owner, "reference", image_bytes(), "../../etc/<evil>.png", designId=design_id)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "evil.png"
    assert body["contentType"] == "image/png"
    assert (body["width"], body["height"]) == (40, 30)
    assert body["isImage"] is True
    served = await content(client, body["url"])
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    assert served.headers["x-content-type-options"] == "nosniff"
    assert Image.open(io.BytesIO(served.content)).size == (40, 30)

    listed = await client.get(URL, headers=owner, params={"designId": design_id})
    assert [item["id"] for item in listed.json()["items"]] == [body["id"]]


async def test_photo_metadata_is_stripped(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    owner = auth_headers(uuid.uuid4())
    design_id = await _client_with_design(client, owner, cities["almaty"])
    exif = Image.Exif()
    exif[0x010F] = "SecretPhone"  # Make

    response = await upload(
        client, owner, "room", image_bytes("JPEG", exif=exif.tobytes()), "room.jpg", designId=design_id
    )

    served = await content(client, response.json()["url"])
    assert b"SecretPhone" not in served.content
    assert response.json()["name"] == "room.jpg"


@pytest.mark.parametrize(
    ("purpose", "data", "status_code"),
    [
        ("reference", b"<html><script>alert(1)</script></html>", 415),
        ("reference", b"%PDF-1.7\n%fake", 415),
        ("document", b"%PDF-1.7\n%fake", 201),
        ("reference", b"", 415),
        ("reference", b"GIF89a" + b"\x00" * 20, 415),
    ],
    ids=["html-as-png", "pdf-not-allowed", "pdf-allowed", "empty", "broken-gif"],
)
async def test_content_decides_the_type(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    cities: dict[str, uuid.UUID],
    purpose: str,
    data: bytes,
    status_code: int,
) -> None:
    owner = auth_headers(uuid.uuid4())
    design_id = await _client_with_design(client, owner, cities["almaty"])

    response = await upload(client, owner, purpose, data, designId=design_id)

    assert response.status_code == status_code, response.text
    if status_code == 415:
        assert response.json()["code"] == "file_type_not_allowed"


async def test_size_and_count_limits(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    owner = auth_headers(uuid.uuid4())
    design_id = await _client_with_design(client, owner, cities["almaty"])

    too_big = await upload(client, owner, "reference", b"\x89PNG" + b"\x00" * (10 * 1024 * 1024), designId=design_id)
    for _ in range(10):
        await upload(client, owner, "reference", image_bytes(), designId=design_id)
    eleventh = await upload(client, owner, "reference", image_bytes(), designId=design_id)

    assert too_big.status_code == 413
    assert too_big.json()["code"] == "file_too_large"
    assert eleventh.status_code == 409
    assert eleventh.json()["code"] == "too_many_files"


async def test_strangers_cannot_touch_private_files(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    owner = auth_headers(uuid.uuid4())
    stranger = auth_headers(uuid.uuid4())
    design_id = await _client_with_design(client, owner, cities["almaty"])
    attachment = (await upload(client, owner, "reference", image_bytes(), designId=design_id)).json()

    listed = await client.get(URL, headers=stranger, params={"designId": design_id})
    as_guest = await client.get(URL, params={"designId": design_id})
    uploaded = await upload(client, stranger, "reference", image_bytes(), designId=design_id)
    deleted = await client.delete(f"{URL}/{attachment['id']}", headers=stranger)
    renamed = await client.patch(f"{URL}/{attachment['id']}", headers=stranger, json={"caption": "мой"})

    assert listed.status_code == 403
    assert as_guest.status_code == 403
    assert uploaded.status_code == 403
    assert deleted.status_code == 403
    assert renamed.status_code == 403


async def test_download_link_must_be_signed(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    owner = auth_headers(uuid.uuid4())
    design_id = await _client_with_design(client, owner, cities["almaty"])
    attachment = (await upload(client, owner, "reference", image_bytes(), designId=design_id)).json()
    path = f"{URL}/{attachment['id']}/content"

    forged = await client.get(path, params={"expires": 9999999999, "signature": "0" * 64})
    expired = await client.get(path, params={"expires": 1, "signature": "0" * 64})

    assert forged.status_code == 403
    assert expired.status_code == 403


async def test_order_gets_a_snapshot_of_design_files(
    client: AsyncClient,
    auth_headers: AuthHeaders,
    role_granter: FakeRoleGranter,
    cities: dict[str, uuid.UUID],
    workshop_body: dict[str, Any],
) -> None:
    owner = auth_headers(uuid.uuid4())
    design_id = await _client_with_design(client, owner, cities["almaty"])
    await upload(client, owner, "room", image_bytes(), "room.png", designId=design_id)
    order = await client.post(
        "/api/v1/orders", headers=owner, json={"designId": design_id, "cityId": str(cities["almaty"])}
    )
    workshop = await _approved_workshop(client, auth_headers, workshop_body, "Цех")
    order_id = order.json()["id"]

    for_workshop = await client.get(URL, headers=workshop, params={"orderId": order_id})
    for_stranger = await client.get(URL, headers=auth_headers(uuid.uuid4()), params={"orderId": order_id})
    await client.delete(f"/api/v1/designs/{design_id}", headers=owner)
    after_design_deleted = await client.get(URL, headers=owner, params={"orderId": order_id})

    assert [item["name"] for item in for_workshop.json()["items"]] == ["room.png"]
    assert for_stranger.status_code == 403
    file_url = after_design_deleted.json()["items"][0]["url"]
    assert (await content(client, file_url)).status_code == 200


async def test_order_files_are_read_only_once_closed(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    owner = auth_headers(uuid.uuid4())
    order_id = await _published_order(client, owner, cities["almaty"])
    added = await upload(client, owner, "document", b"%PDF-1.4\n%x", "plan.pdf", orderId=order_id)
    await client.post(f"/api/v1/orders/{order_id}/cancel", headers=owner)

    late = await upload(client, owner, "document", b"%PDF-1.4\n%x", orderId=order_id)

    assert added.status_code == 201
    assert late.json()["code"] == "invalid_status"


async def test_workshop_gallery_is_public_after_approval(
    client: AsyncClient, auth_headers: AuthHeaders, role_granter: FakeRoleGranter, workshop_body: dict[str, Any]
) -> None:
    owner = auth_headers(uuid.uuid4())
    workshop = await client.put("/api/v1/workshops/mine", headers=owner, json=workshop_body)
    workshop_id = workshop.json()["id"]
    first = (await upload(client, owner, "workshop_portfolio", image_bytes())).json()
    second = (await upload(client, owner, "workshop_portfolio", image_bytes())).json()
    await upload(client, owner, "workshop_logo", image_bytes())
    logo = (await upload(client, owner, "workshop_logo", image_bytes(size=(64, 64)))).json()

    hidden = await client.get(URL, params={"workshopId": workshop_id})
    admin = auth_headers(uuid.uuid4(), roles=(UserRoleEnum.ADMIN,))
    await client.post(f"/api/v1/workshops/{workshop_id}/approve", headers=admin)
    reordered = await client.post(f"{URL}/reorder", headers=owner, json={"ids": [second["id"], first["id"]]})
    public = await client.get(URL, params={"workshopId": workshop_id})

    assert hidden.status_code == 404
    items = public.json()["items"]
    logos = [item for item in items if item["purpose"] == "workshop_logo"]
    assert [item["id"] for item in logos] == [logo["id"]]
    portfolio = [item["id"] for item in items if item["purpose"] == "workshop_portfolio"]
    assert portfolio == [second["id"], first["id"]]
    assert reordered.status_code == 200


async def test_reorder_rejects_mixed_galleries(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID]
) -> None:
    owner = auth_headers(uuid.uuid4())
    first_design = await _client_with_design(client, owner, cities["almaty"])
    second_design = await _client_with_design(client, owner, cities["almaty"])
    one = (await upload(client, owner, "reference", image_bytes(), designId=first_design)).json()
    two = (await upload(client, owner, "reference", image_bytes(), designId=second_design)).json()

    response = await client.post(f"{URL}/reorder", headers=owner, json={"ids": [one["id"], two["id"]]})

    assert response.json()["code"] == "attachment_target"
