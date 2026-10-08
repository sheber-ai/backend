from collections import Counter

from fastapi import FastAPI


def test_operation_ids_are_unique(app: FastAPI) -> None:
    """Orval derives hook names from operationId."""
    operation_ids = [
        operation["operationId"] for path in app.openapi()["paths"].values() for operation in path.values()
    ]

    duplicates = [name for name, count in Counter(operation_ids).items() if count > 1]
    assert not duplicates, f"Duplicate endpoint names: {duplicates}"


def test_every_operation_has_tag(app: FastAPI) -> None:
    """Orval splits generated code by tag."""
    untagged = [
        operation["operationId"]
        for path in app.openapi()["paths"].values()
        for operation in path.values()
        if not operation.get("tags")
    ]
    assert not untagged, f"Endpoints without tag: {untagged}"
