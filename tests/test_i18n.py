import pytest

from common.i18n import localize, parse_accept_language
from enums.i18n_enum import LanguageEnum


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, LanguageEnum.RU),
        ("kk", LanguageEnum.KK),
        ("en-GB,en;q=0.9", LanguageEnum.EN),
        ("de;q=1.0,kk;q=0.5,ru;q=0.8", LanguageEnum.RU),
        ("fr, de", LanguageEnum.RU),
        ("kk;q=oops", LanguageEnum.RU),
    ],
    ids=["missing", "plain", "region", "by-quality", "unsupported", "broken-quality"],
)
def test_parse_accept_language(header: str | None, expected: LanguageEnum) -> None:
    assert parse_accept_language(header) == expected


def test_localize_falls_back_to_russian() -> None:
    assert localize({"ru": "Шкаф", "en": "Wardrobe"}, LanguageEnum.KK) == "Шкаф"
    assert localize({"en": "Wardrobe"}, LanguageEnum.KK) == "Wardrobe"
