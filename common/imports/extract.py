import json
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit

MAX_IMAGES = 6
MAX_TEXT = 2000

# UN/CEFACT unit codes schema.org uses for QuantitativeValue
_UNIT_TO_MM = {"MMT": 1.0, "CMT": 10.0, "MTR": 1000.0, "mm": 1.0, "cm": 10.0, "m": 1000.0, "мм": 1.0, "см": 10.0}


@dataclass
class ProductData:
    """What a shop page tells about a product. Every field may be missing."""

    title: str | None = None
    description: str | None = None
    images: list[str] = field(default_factory=list)
    price: float | None = None
    currency: str | None = None
    brand: str | None = None
    site_name: str | None = None
    width_mm: int | None = None
    height_mm: int | None = None
    depth_mm: int | None = None
    structured: bool = False

    @property
    def empty(self) -> bool:
        return not (self.title or self.images or self.description)


class _HeadParser(HTMLParser):
    """Collects meta tags, <title> and JSON-LD blocks. Scripts are read as text, never run."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title = ""
        self.ld_json: list[str] = []
        self._in_title = False
        self._in_ld = False
        self._buffer: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "meta":
            key = (values.get("property") or values.get("name") or values.get("itemprop") or "").lower()
            if key and "content" in values and key not in self.meta:
                self.meta[key] = values["content"]
        elif tag == "title":
            self._in_title = True
        elif tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._in_ld = True
            self._buffer = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_ld:
            self._in_ld = False
            self.ld_json.append("".join(self._buffer))

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif self._in_ld:
            self._buffer.append(data)


def _clean(value: Any, limit: int = MAX_TEXT) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(unescape(value).split())
    return text[:limit] or None


def _products(node: Any) -> list[dict[str, Any]]:
    """Every schema.org Product in a JSON-LD tree (top level, lists, @graph)."""
    found: list[dict[str, Any]] = []
    if isinstance(node, list):
        for item in node:
            found += _products(item)
    elif isinstance(node, dict):
        kind = node.get("@type")
        kinds = kind if isinstance(kind, list) else [kind]
        if "Product" in kinds:
            found.append(node)
        if "@graph" in node:
            found += _products(node["@graph"])
    return found


def _to_mm(value: Any) -> int | None:
    if isinstance(value, dict):
        unit = str(value.get("unitCode") or value.get("unitText") or "CMT")
        try:
            return round(float(str(value.get("value"))) * _UNIT_TO_MM.get(unit, 10.0))
        except ValueError:
            return None
    if isinstance(value, str):
        parts = value.replace(",", ".").split()
        try:
            number = float(parts[0])
        except (IndexError, ValueError):
            return None
        unit = parts[1] if len(parts) > 1 else "cm"
        return round(number * _UNIT_TO_MM.get(unit, 10.0))
    return None


def _images(value: Any) -> list[str]:
    items = value if isinstance(value, list) else [value]
    urls: list[str] = []
    for item in items:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict) and isinstance(item.get("url"), str):
            urls.append(item["url"])
    return urls


def _absolute_images(urls: list[str], base: str) -> list[str]:
    result: list[str] = []
    for url in urls:
        absolute = urljoin(base, url.strip())
        if urlsplit(absolute).scheme in ("http", "https") and absolute not in result:
            result.append(absolute)
    return result[:MAX_IMAGES]


def extract_product(html: str, base_url: str) -> ProductData:
    parser = _HeadParser()
    parser.feed(html)
    data = ProductData()
    images: list[str] = []

    for block in parser.ld_json:
        try:
            parsed = json.loads(block)
        except ValueError:
            continue
        for product in _products(parsed):
            data.structured = True
            data.title = data.title or _clean(product.get("name"), 256)
            data.description = data.description or _clean(product.get("description"))
            images += _images(product.get("image"))
            brand = product.get("brand")
            data.brand = data.brand or _clean(brand.get("name") if isinstance(brand, dict) else brand, 128)
            offers = product.get("offers")
            offer = offers[0] if isinstance(offers, list) and offers else offers
            if isinstance(offer, dict) and data.price is None:
                try:
                    data.price = float(str(offer.get("price")).replace(",", "."))
                except ValueError:
                    data.price = None
                data.currency = _clean(offer.get("priceCurrency"), 8)
            data.width_mm = data.width_mm or _to_mm(product.get("width"))
            data.height_mm = data.height_mm or _to_mm(product.get("height"))
            data.depth_mm = data.depth_mm or _to_mm(product.get("depth"))

    meta = parser.meta
    data.title = data.title or _clean(meta.get("og:title"), 256) or _clean(parser.title, 256)
    data.description = data.description or _clean(meta.get("og:description")) or _clean(meta.get("description"))
    data.site_name = _clean(meta.get("og:site_name"), 128) or urlsplit(base_url).hostname
    images += [meta[key] for key in ("og:image", "og:image:url", "twitter:image") if meta.get(key)]
    if data.price is None and meta.get("product:price:amount"):
        try:
            data.price = float(meta["product:price:amount"].replace(",", "."))
            data.currency = _clean(meta.get("product:price:currency"), 8)
        except ValueError:
            data.price = None
    data.images = _absolute_images(images, base_url)
    return data
