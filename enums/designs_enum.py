from enum import StrEnum


class FurnitureTypeEnum(StrEnum):
    WARDROBE = "wardrobe"
    SHELVING = "shelving"
    DRESSER = "dresser"


class DesignSourceEnum(StrEnum):
    """Where the design started. `link` and `photo` keep the reference until AI import lands."""

    SCRATCH = "scratch"
    LINK = "link"
    PHOTO = "photo"


class MaterialEnum(StrEnum):
    """Mirrors MATERIALS in frontend/src/shared/design/materials.ts."""

    OAK = "oak"
    WALNUT = "walnut"
    IVORY = "ivory"
    SAGE = "sage"
    GRAPHITE = "graphite"
