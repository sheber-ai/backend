from collections import Counter

from fastapi import FastAPI


def test_operation_ids_are_unique(app: FastAPI) -> None:
    """operationId = имя функции-эндпоинта, из него Orval строит имена хуков на фронте."""
    operation_ids = [
        operation["operationId"] for path in app.openapi()["paths"].values() for operation in path.values()
    ]

    duplicates = [name for name, count in Counter(operation_ids).items() if count > 1]
    assert not duplicates, f"Неуникальные имена эндпоинтов: {duplicates}"


def test_every_operation_has_tag(app: FastAPI) -> None:
    """Тег = домен. Orval раскладывает сгенерированные хуки по папкам тегов."""
    untagged = [
        operation["operationId"]
        for path in app.openapi()["paths"].values()
        for operation in path.values()
        if not operation.get("tags")
    ]
    assert not untagged, f"Эндпоинты без тега: {untagged}"
