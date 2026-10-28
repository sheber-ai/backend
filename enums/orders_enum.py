from enum import StrEnum


class OrderStatusEnum(StrEnum):
    PUBLISHED = "published"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrderGroupEnum(StrEnum):
    """Tab of the client's order list."""

    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
