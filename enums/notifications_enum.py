from enum import StrEnum


class NotificationKindEnum(StrEnum):
    NEW_ORDER = "new_order"
    OFFER_RECEIVED = "offer_received"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    MESSAGE_RECEIVED = "message_received"
    ORDER_STARTED = "order_started"
    ORDER_COMPLETED = "order_completed"
    ORDER_CANCELLED = "order_cancelled"
    WORKSHOP_APPROVED = "workshop_approved"
    WORKSHOP_REJECTED = "workshop_rejected"
    REVIEW_RECEIVED = "review_received"
    REVIEW_REPLIED = "review_replied"
