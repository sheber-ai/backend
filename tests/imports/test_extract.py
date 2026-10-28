from common.imports.extract import extract_product

PRODUCT_PAGE = """
<html><head>
<title>Шкаф «Север» — купить</title>
<meta property="og:site_name" content="Мебель Плюс">
<meta property="og:image" content="/img/og.jpg">
<script type="application/ld+json">
{"@context": "https://schema.org", "@graph": [
  {"@type": "Organization", "name": "Мебель Плюс"},
  {"@type": "Product", "name": "Шкаф-купе &laquo;Север&raquo;", "description": "Двухдверный шкаф,  ЛДСП",
   "image": ["https://cdn.shop.kz/1.jpg", {"url": "/img/2.jpg"}],
   "brand": {"@type": "Brand", "name": "Север"},
   "offers": {"@type": "Offer", "price": "189990", "priceCurrency": "KZT"},
   "width": {"@type": "QuantitativeValue", "value": 180, "unitCode": "CMT"},
   "height": {"@type": "QuantitativeValue", "value": 2.4, "unitCode": "MTR"},
   "depth": "60 см"}
]}
</script>
<script>window.evil = fetch('/steal')</script>
</head><body></body></html>
"""


def test_reads_schema_org_product() -> None:
    product = extract_product(PRODUCT_PAGE, "https://shop.kz/catalog/sever")

    assert product.structured is True
    assert product.title == "Шкаф-купе «Север»"
    assert product.description == "Двухдверный шкаф, ЛДСП"
    assert product.images == ["https://cdn.shop.kz/1.jpg", "https://shop.kz/img/2.jpg", "https://shop.kz/img/og.jpg"]
    assert (product.price, product.currency, product.brand) == (189990.0, "KZT", "Север")
    assert (product.width_mm, product.height_mm, product.depth_mm) == (1800, 2400, 600)
    assert product.site_name == "Мебель Плюс"


def test_falls_back_to_open_graph() -> None:
    page = """<meta property="og:title" content="Комод"><meta name="description" content="Белый комод">
    <meta property="og:image" content="https://shop.kz/c.png"><meta property="product:price:amount" content="45000">"""

    product = extract_product(page, "https://shop.kz/c")

    assert product.structured is False
    assert (product.title, product.description, product.price) == ("Комод", "Белый комод", 45000.0)
    assert product.images == ["https://shop.kz/c.png"]
    assert product.site_name == "shop.kz"


def test_page_without_data_is_empty_and_drops_bad_image_links() -> None:
    product = extract_product('<meta property="og:image" content="javascript:alert(1)">', "https://x.kz/")

    assert product.images == []
    assert product.empty is True
