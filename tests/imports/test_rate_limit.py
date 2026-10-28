import asyncio
import uuid
from collections.abc import Iterator

import pytest
from aioinject import Object
from aioinject.testing import TestContainer
from httpx import AsyncClient
from sqlalchemy import func, select, update

from common.database import session_maker
from models.imports.mdl_import_request import ImportRequest
from services.di.container import create_container
from settings.imports_settings import ImportsSettings
from tests.conftest import AuthHeaders

pytestmark = pytest.mark.db

BLOCKED = {"url": "http://127.0.0.1/admin"}


@pytest.fixture
def three_per_window() -> Iterator[None]:
    settings = ImportsSettings(rate_limit=3, rate_window_seconds=600)
    with TestContainer(create_container()).override(Object(settings, interface=ImportsSettings)):
        yield


async def _attempts(user_id: uuid.UUID) -> int:
    async with session_maker() as session:
        return await session.scalar(select(func.count()).where(ImportRequest.user_id == user_id)) or 0


async def test_import_stops_after_the_limit_and_says_when_to_retry(
    client: AsyncClient, auth_headers: AuthHeaders, three_per_window: None
) -> None:
    headers = auth_headers(uuid.uuid4())
    # Failed reads count too: otherwise the limit would not protect from probing addresses
    codes = [
        (await client.post("/api/v1/imports/preview", headers=headers, json=BLOCKED)).json()["code"] for _ in range(3)
    ]
    limited = await client.post("/api/v1/imports/preview", headers=headers, json=BLOCKED)
    images = await client.post(
        "/api/v1/imports/images",
        headers=headers,
        json={"designId": str(uuid.uuid4()), "imageUrls": ["https://shop.example/a.png"], "source": "shop"},
    )

    assert codes == ["import_blocked"] * 3
    assert limited.status_code == 429
    assert limited.json()["code"] == "import_rate_limited"
    assert 590 <= int(limited.headers["retry-after"]) <= 600
    assert images.json()["code"] == "import_rate_limited"


async def test_import_limit_is_per_user(client: AsyncClient, auth_headers: AuthHeaders, three_per_window: None) -> None:
    first = auth_headers(uuid.uuid4())
    for _ in range(3):
        await client.post("/api/v1/imports/preview", headers=first, json=BLOCKED)

    other = await client.post("/api/v1/imports/preview", headers=auth_headers(uuid.uuid4()), json=BLOCKED)

    assert other.json()["code"] == "import_blocked"


async def test_parallel_requests_do_not_slip_past_the_limit(
    client: AsyncClient, auth_headers: AuthHeaders, three_per_window: None
) -> None:
    user_id = uuid.uuid4()
    headers = auth_headers(user_id)
    await client.get("/api/v1/users/me", headers=headers)

    responses = await asyncio.gather(
        *(client.post("/api/v1/imports/preview", headers=headers, json=BLOCKED) for _ in range(8))
    )

    codes = sorted(response.json()["code"] for response in responses)
    assert codes == ["import_blocked"] * 3 + ["import_rate_limited"] * 5
    assert await _attempts(user_id) == 3


async def test_old_attempts_leave_the_window(
    client: AsyncClient, auth_headers: AuthHeaders, three_per_window: None
) -> None:
    user_id = uuid.uuid4()
    headers = auth_headers(user_id)
    for _ in range(3):
        await client.post("/api/v1/imports/preview", headers=headers, json=BLOCKED)
    async with session_maker() as session:
        await session.execute(
            update(ImportRequest)
            .where(ImportRequest.user_id == user_id)
            .values(created_at=func.now() - func.make_interval(0, 0, 0, 0, 0, 11))
        )
        await session.commit()

    again = await client.post("/api/v1/imports/preview", headers=headers, json=BLOCKED)

    assert again.json()["code"] == "import_blocked"
    # Expired attempts are purged, only the fresh one stays
    assert await _attempts(user_id) == 1
