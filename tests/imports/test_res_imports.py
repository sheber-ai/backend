import io
import uuid
from collections.abc import Iterator

import httpx
import pytest
from aioinject import Object
from aioinject.testing import TestContainer
from httpx import AsyncClient
from PIL import Image

from common.imports.safe_fetch import SafeFetcher
from services.di.container import create_container
from tests.conftest import AuthHeaders
from tests.orders.test_order_flow import _client_with_design

PAGE = """<html><head><meta property="og:title" content="Стеллаж «Лофт»">
<meta property="og:image" content="https://shop.example/a.png"></head></html>"""


def _png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (30, 20), (90, 60, 30)).save(out, "PNG")
    return out.getvalue()


def _handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/robots.txt":
        return httpx.Response(404)
    if path == "/item":
        return httpx.Response(200, headers={"content-type": "text/html"}, text=PAGE)
    if path == "/a.png":
        return httpx.Response(200, headers={"content-type": "image/png"}, content=_png())
    if path == "/fake.png":
        return httpx.Response(200, headers={"content-type": "image/png"}, content=b"<svg onload=alert(1)>")
    return httpx.Response(404)


async def _public(host: str, port: int) -> list[str]:
    return ["93.184.216.34"]


@pytest.fixture
def shop() -> Iterator[None]:
    fake = SafeFetcher(resolver=_public, transport=httpx.MockTransport(_handler))
    with TestContainer(create_container()).override(Object(fake, interface=SafeFetcher)):
        yield


@pytest.mark.db
async def test_preview_reads_the_page(client: AsyncClient, auth_headers: AuthHeaders, shop: None) -> None:
    response = await client.post(
        "/api/v1/imports/preview", headers=auth_headers(uuid.uuid4()), json={"url": "shop.example/item"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["title"] == "Стеллаж «Лофт»"
    assert response.json()["source"] == "shop.example"
    assert response.json()["images"] == ["https://shop.example/a.png"]


@pytest.mark.db
async def test_preview_explains_blocked_links(client: AsyncClient, auth_headers: AuthHeaders) -> None:
    response = await client.post(
        "/api/v1/imports/preview", headers=auth_headers(uuid.uuid4()), json={"url": "http://127.0.0.1/admin"}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "import_blocked"


async def test_preview_requires_sign_in(client: AsyncClient) -> None:
    response = await client.post("/api/v1/imports/preview", json={"url": "https://shop.example/item"})

    assert response.status_code == 401


@pytest.mark.db
async def test_picked_images_become_design_references(
    client: AsyncClient, auth_headers: AuthHeaders, cities: dict[str, uuid.UUID], shop: None
) -> None:
    owner = auth_headers(uuid.uuid4())
    design_id = await _client_with_design(client, owner, cities["almaty"])
    body = {
        "designId": design_id,
        "imageUrls": ["https://shop.example/a.png", "https://shop.example/fake.png", "https://shop.example/gone.png"],
        "source": "shop.example",
    }

    response = await client.post("/api/v1/imports/images", headers=owner, json=body)
    stranger = await client.post("/api/v1/imports/images", headers=auth_headers(uuid.uuid4()), json=body)

    assert response.status_code == 200, response.text
    attached = response.json()["attached"]
    assert [(item["purpose"], item["caption"]) for item in attached] == [("reference", "shop.example")]
    assert response.json()["failed"] == 2
    assert stranger.status_code == 403
