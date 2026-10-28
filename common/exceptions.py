from fastapi import status


class AppError(Exception):
    """Base domain error, mapped to an HTTP response in rest_api."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "bad_request"
    headers: dict[str, str] | None = None

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class PermissionDeniedError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "permission_denied"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"


class ServiceUnavailableError(AppError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    code = "service_unavailable"


class InvalidStatusError(ConflictError):
    code = "invalid_status"


class ProfileIncompleteError(AppError):
    code = "profile_incomplete"


class WorkshopRequiredError(PermissionDeniedError):
    """The user has no approved workshop."""

    code = "workshop_required"


class OfferExistsError(ConflictError):
    code = "offer_exists"


class CityNotFoundError(AppError):
    code = "city_not_found"


class ThreadRequiredError(AppError):
    """The order owner must say which workshop the chat is with."""

    code = "thread_required"


class DesignAlreadyPublishedError(ConflictError):
    """The design already has an order that is not finished."""

    code = "already_published"


class PayloadTooLargeError(AppError):
    status_code = status.HTTP_413_CONTENT_TOO_LARGE
    code = "file_too_large"


class UnsupportedFileTypeError(AppError):
    status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    code = "file_type_not_allowed"


class AttachmentLimitError(ConflictError):
    code = "too_many_files"


class AttachmentTargetError(AppError):
    """The upload names no target or a target that does not fit the purpose."""

    code = "attachment_target"


class SourceImportError(AppError):
    """A shop page or image could not be imported; `code` tells the user why."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


class ImportRateLimitedError(AppError):
    """Too many link reads by one user in the rate window."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "import_rate_limited"

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Too many imports, retry in {retry_after} s")
        self.headers = {"Retry-After": str(retry_after)}


class ReviewNotAllowedError(ConflictError):
    """Only the client of a completed order reviews, and only the workshop that did it."""

    code = "review_not_allowed"
