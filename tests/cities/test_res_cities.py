import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.db


@pytest.mark.parametrize(
    ("accept_language", "names"),
    [
        (None, ["Алматы", "Усть-Каменогорск"]),
        ("kk-KZ,kk;q=0.9", ["Алматы", "Өскемен"]),
        ("en", ["Almaty", "Oskemen"]),
        ("de-DE", ["Алматы", "Усть-Каменогорск"]),
    ],
    ids=["default", "kazakh", "english", "unsupported-falls-back"],
)
async def test_list_cities_is_localized(
    client: AsyncClient, cities: dict[str, uuid.UUID], accept_language: str | None, names: list[str]
) -> None:
    headers = {"Accept-Language": accept_language} if accept_language else {}

    response = await client.get("/api/v1/cities", headers=headers)

    assert [city["name"] for city in response.json()["items"]] == names


async def test_list_cities_hides_inactive(client: AsyncClient, cities: dict[str, uuid.UUID]) -> None:
    response = await client.get("/api/v1/cities")

    assert "hidden" not in [city["slug"] for city in response.json()["items"]]
