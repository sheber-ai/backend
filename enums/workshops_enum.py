from enum import StrEnum


class WorkshopStatusEnum(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class WorkshopServiceEnum(StrEnum):
    """What a workshop does besides manufacturing."""

    MEASUREMENT = "measurement"
    DESIGN_PROJECT = "design_project"
    DELIVERY = "delivery"
    INSTALLATION = "installation"
    DISMANTLING = "dismantling"


class WorkshopMaterialEnum(StrEnum):
    """Board and finishing materials a workshop works with."""

    CHIPBOARD = "chipboard"
    MDF = "mdf"
    VENEER = "veneer"
    SOLID_WOOD = "solid_wood"
    PLYWOOD = "plywood"
    GLASS = "glass"
