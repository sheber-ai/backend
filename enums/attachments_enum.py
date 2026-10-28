from enum import StrEnum


class AttachmentPurposeEnum(StrEnum):
    """What a file is for. Decides where it hangs, who sees it and which limits apply."""

    WORKSHOP_LOGO = "workshop_logo"
    WORKSHOP_PORTFOLIO = "workshop_portfolio"
    REFERENCE = "reference"
    ROOM = "room"
    DOCUMENT = "document"
