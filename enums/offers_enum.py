from enum import StrEnum


class OfferStatusEnum(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class OfferTabEnum(StrEnum):
    """Tab of the workshop's offer list: active = still waiting or being worked on."""

    ACTIVE = "active"
    ARCHIVE = "archive"
