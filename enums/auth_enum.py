from enum import StrEnum


class UserRoleEnum(StrEnum):
    """Keycloak realm roles known to the app. Others are ignored."""

    CLIENT = "client"
    CONTRACTOR = "contractor"
    ADMIN = "admin"
