import httpx
import pytest

from common.imports.safe_fetch import FetchError, SafeFetcher, normalize_url

PUBLIC_IP = "93.184.216.34"


def resolver_for(table: dict[str, list[str]]):  # type: ignore[no-untyped-def]
    async def resolve(host: str, port: int) -> list[str]:
        return table.get(host, [PUBLIC_IP])

    return resolve


def fetcher(handler, table: dict[str, list[str]] | None = None) -> SafeFetcher:  # type: ignore[no-untyped-def]
    return SafeFetcher(resolver=resolver_for(table or {}), transport=httpx.MockTransport(handler))


def html(body: str = "<html></html>") -> httpx.Response:
    return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=body)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("shop.kz/item/1", "https://shop.kz/item/1"),
        ("  HTTPS://Shop.KZ/a?x=1#reviews ", "https://shop.kz/a?x=1"),
        ("http://shop.kz", "http://shop.kz/"),
    ],
)
def test_normalize_url(raw: str, expected: str) -> None:
    assert normalize_url(raw) == expected


@pytest.mark.parametrize(
    "raw", ["ftp://shop.kz/a", "file:///etc/passwd", "javascript:alert(1)", "https://u:p@shop.kz/"]
)
def test_normalize_rejects_other_schemes_and_credentials(raw: str) -> None:
    with pytest.raises(FetchError) as error:
        normalize_url(raw)
    assert error.value.code == "import_bad_url"


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.5", "192.168.1.10", "172.16.0.1", "169.254.169.254", "::1", "::ffff:127.0.0.1", "0.0.0.0"],
)
async def test_private_networks_are_blocked(address: str) -> None:
    def never(_: httpx.Request) -> httpx.Response:
        raise AssertionError("must not connect")

    with pytest.raises(FetchError) as error:
        await fetcher(never, {"evil.example": [address]}).fetch(
            "https://evil.example/", accept=("text/html",), max_bytes=1000
        )
    assert error.value.code == "import_blocked"


async def test_non_standard_ports_are_blocked() -> None:
    with pytest.raises(FetchError) as error:
        await fetcher(lambda _: html()).fetch("http://shop.example:8080/", accept=("text/html",), max_bytes=1000)
    assert error.value.code == "import_blocked"


async def test_connects_to_the_checked_address() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return html("<title>ok</title>")

    result = await fetcher(handler).fetch("https://shop.example/item", accept=("text/html",), max_bytes=1000)

    assert result.body == b"<title>ok</title>"
    assert seen[0].url.host == PUBLIC_IP
    assert seen[0].headers["host"] == "shop.example"
    assert "SheberBot" in seen[0].headers["user-agent"]


async def test_redirect_into_a_private_network_is_blocked() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://admin.internal/"})

    with pytest.raises(FetchError) as error:
        await fetcher(handler, {"admin.internal": ["10.1.2.3"]}).fetch(
            "https://shop.example/", accept=("text/html",), max_bytes=1000
        )
    assert error.value.code == "import_blocked"


async def test_size_type_and_status_limits() -> None:
    big = fetcher(lambda _: html("x" * 5000))
    json_page = fetcher(lambda _: httpx.Response(200, headers={"content-type": "application/json"}, text="{}"))
    refused = fetcher(lambda _: httpx.Response(403))

    for client, code in ((big, "import_too_large"), (json_page, "import_unsupported"), (refused, "import_not_allowed")):
        with pytest.raises(FetchError) as error:
            await client.fetch("https://shop.example/", accept=("text/html",), max_bytes=1000)
        assert error.value.code == code


async def test_robots_txt_is_respected() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200, headers={"content-type": "text/plain"}, text="User-agent: *\nDisallow: /private/\n"
            )
        return html()

    client = fetcher(handler)
    assert await client.allowed_by_robots("https://shop.example/catalog/1") is True
    assert await client.allowed_by_robots("https://shop.example/private/1") is False
