import copy

import pytest
from pydantic import ValidationError

from schemas.designs.sch_document import DesignDocumentSchema
from tests.samples import WARDROBE_DOCUMENT


def test_document_round_trips() -> None:
    document = DesignDocumentSchema.model_validate(WARDROBE_DOCUMENT)

    assert document.model_dump(mode="json", by_alias=True) == WARDROBE_DOCUMENT


def test_document_rejects_duplicate_ids() -> None:
    document = copy.deepcopy(WARDROBE_DOCUMENT)
    document["layout"]["children"][1]["node"]["id"] = "a1"

    with pytest.raises(ValidationError, match="duplicate node id"):
        DesignDocumentSchema.model_validate(document)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("size", "width"), 5000),
        (("plinth",), -10),
        (("materials", "body"), "plastic"),
        (("facade", "type"), "folding"),
    ],
    ids=["too-wide", "negative-plinth", "unknown-material", "unknown-facade"],
)
def test_document_rejects_invalid_values(path: tuple[str, ...], value: object) -> None:
    document = copy.deepcopy(WARDROBE_DOCUMENT)
    target = document
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value

    with pytest.raises(ValidationError):
        DesignDocumentSchema.model_validate(document)


def test_split_needs_two_children() -> None:
    document = copy.deepcopy(WARDROBE_DOCUMENT)
    document["layout"]["children"] = document["layout"]["children"][:1]

    with pytest.raises(ValidationError):
        DesignDocumentSchema.model_validate(document)
