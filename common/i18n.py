from collections.abc import Mapping

from enums.i18n_enum import DEFAULT_LANGUAGE, LanguageEnum


def localize(text: Mapping[str, str], language: LanguageEnum) -> str:
    """Picks a translation: requested language, then the default one, then any."""
    return text.get(language) or text.get(DEFAULT_LANGUAGE) or next(iter(text.values()), "")


def parse_accept_language(header: str | None) -> LanguageEnum:
    """First supported language from an Accept-Language header, e.g. `kk-KZ,kk;q=0.9,ru;q=0.8`."""
    if not header:
        return DEFAULT_LANGUAGE
    ranked: list[tuple[float, str]] = []
    for part in header.split(","):
        tag, _, params = part.strip().partition(";")
        quality = 1.0
        if params.strip().startswith("q="):
            try:
                quality = float(params.strip()[2:])
            except ValueError:
                quality = 0.0
        # q=0 means "not acceptable"
        if quality > 0:
            ranked.append((quality, tag.split("-")[0].lower()))
    supported = {language.value for language in LanguageEnum}
    for _, code in sorted(ranked, key=lambda item: item[0], reverse=True):
        if code in supported:
            return LanguageEnum(code)
    return DEFAULT_LANGUAGE
