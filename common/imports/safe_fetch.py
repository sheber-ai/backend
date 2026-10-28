import asyncio
import ipaddress
import re
import socket
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = "SheberBot/1.0 (+https://sheber.kz/bot; furniture reference import)"
TIMEOUT = httpx.Timeout(8.0, connect=4.0)
MAX_REDIRECTS = 3
ALLOWED_PORTS = {80, 443}
_OTHER_SCHEME = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:(?!//)")
_HOST_PORT = re.compile(r"^[^:/]+:\d+(/|$)")

type Resolver = Callable[[str, int], Awaitable[list[str]]]


class FetchError(Exception):
    """Why a remote resource cannot be used. `code` is the API error code."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class Fetched:
    url: str
    content_type: str
    body: bytes


async def resolve_host(host: str, port: int) -> list[str]:
    infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return sorted({str(info[4][0]) for info in infos})


def normalize_url(raw: str) -> str:
    """Trims, adds https:// when no scheme was typed, drops the #fragment. Rejects anything but http(s)."""
    value = raw.strip()
    # "javascript:…", "mailto:…" and the like; "shop.kz:443/x" is a host with a port
    if _OTHER_SCHEME.match(value) and not _HOST_PORT.match(value):
        raise FetchError("import_bad_url", "Only http and https links are supported")
    if "://" not in value:
        value = f"https://{value}"
    parts = urlsplit(value)
    try:
        parts.port  # noqa: B018 - raises on a malformed port
    except ValueError as error:
        raise FetchError("import_bad_url", "The link has an invalid port") from error
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise FetchError("import_bad_url", "Only http and https links are supported")
    if parts.username or parts.password:
        raise FetchError("import_bad_url", "Links with credentials are not supported")
    return urlunsplit((parts.scheme, parts.netloc.lower(), parts.path or "/", parts.query, ""))


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


class SafeFetcher:
    """GETs public web pages only: no private networks, pinned DNS, bounded size and time, no scripts run."""

    def __init__(self, resolver: Resolver = resolve_host, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._resolver = resolver
        self._transport = transport

    async def fetch(self, url: str, *, accept: tuple[str, ...], max_bytes: int) -> Fetched:
        current = normalize_url(url)
        async with httpx.AsyncClient(transport=self._transport, timeout=TIMEOUT, follow_redirects=False) as client:
            for _ in range(MAX_REDIRECTS + 1):
                response = await self._send(client, current)
                try:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise FetchError("import_unavailable", "Redirect without a target")
                        current = normalize_url(urljoin(current, location))
                        continue
                    if response.status_code in (401, 403, 429):
                        raise FetchError("import_not_allowed", f"The site refused access ({response.status_code})")
                    if response.status_code >= 400:
                        raise FetchError("import_unavailable", f"The site answered {response.status_code}")
                    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    if not content_type.startswith(accept):
                        raise FetchError("import_unsupported", f"Unexpected content type {content_type!r}")
                    body = await self._read_limited(response, max_bytes)
                    return Fetched(url=current, content_type=content_type, body=body)
                finally:
                    await response.aclose()
        raise FetchError("import_unavailable", "Too many redirects")

    async def allowed_by_robots(self, url: str) -> bool:
        parts = urlsplit(normalize_url(url))
        robots_url = urlunsplit((parts.scheme, parts.netloc, "/robots.txt", "", ""))
        try:
            fetched = await self.fetch(robots_url, accept=("text/plain",), max_bytes=256 * 1024)
        except FetchError as error:
            if error.code == "import_blocked":
                raise
            # No robots.txt (or an unreadable one) means no restrictions
            return True
        parser = RobotFileParser()
        parser.parse(fetched.body.decode("utf-8", errors="replace").splitlines())
        return parser.can_fetch(USER_AGENT, url)

    async def _send(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        parts = urlsplit(url)
        host = parts.hostname or ""
        port = parts.port or (443 if parts.scheme == "https" else 80)
        if port not in ALLOWED_PORTS:
            raise FetchError("import_blocked", "Only standard web ports are allowed")
        try:
            addresses = await self._resolver(host, port)
        except OSError as error:
            raise FetchError("import_unavailable", "The site cannot be found") from error
        if not addresses or not all(_is_public(address) for address in addresses):
            raise FetchError("import_blocked", "The link points to a private or local network")
        # Connect to the address we checked, not to whatever DNS answers next (rebinding)
        ip = addresses[0]
        netloc = f"[{ip}]" if ":" in ip else ip
        pinned = urlunsplit((parts.scheme, f"{netloc}:{port}", parts.path or "/", parts.query, ""))
        request = client.build_request(
            "GET",
            pinned,
            headers={"Host": parts.netloc, "User-Agent": USER_AGENT, "Accept": "text/html,image/*;q=0.9"},
            extensions={"sni_hostname": host},
        )
        try:
            return await client.send(request, stream=True)
        except httpx.TimeoutException as error:
            raise FetchError("import_unavailable", "The site took too long to answer") from error
        except httpx.HTTPError as error:
            raise FetchError("import_unavailable", "The site cannot be reached") from error

    @staticmethod
    async def _read_limited(response: httpx.Response, max_bytes: int) -> bytes:
        chunks: list[bytes] = []
        total = 0
        async for chunk in response.aiter_bytes():
            total += len(chunk)
            if total > max_bytes:
                raise FetchError("import_too_large", "The page is too large")
            chunks.append(chunk)
        return b"".join(chunks)
