import pytest
from pydantic import TypeAdapter, ValidationError

from schemas.sch_base import Phone

PHONE: TypeAdapter[str] = TypeAdapter(Phone)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+77011234567", "+77011234567"),
        ("+7 (701) 123-45-67", "+77011234567"),
        ("8 701 123 45 67", "+77011234567"),
        ("87011234567", "+77011234567"),
        ("7011234567", "+77011234567"),
        (" +7 747 123 45 67 ", "+77471234567"),
        ("+7 912 345-67-89", "+79123456789"),
        ("+996 555 123 456", "+996555123456"),
        ("+1 (202) 555-0123", "+12025550123"),
    ],
    ids=["e164", "brackets", "kz-trunk-spaces", "kz-trunk", "kz-national", "padded", "russia", "kyrgyzstan", "usa"],
)
def test_phone_normalizes_to_e164(raw: str, expected: str) -> None:
    assert PHONE.validate_python(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "123", "+7 701 123 45", "+7 701 123 45 678", "8 701 123 45 6", "+1 202 555 0100 12", "+999 123 456 789"],
    ids=["empty", "short", "kz-short", "kz-long", "trunk-short", "usa-long", "unknown-code"],
)
def test_phone_rejects_invalid(raw: str) -> None:
    with pytest.raises(ValidationError):
        PHONE.validate_python(raw)
