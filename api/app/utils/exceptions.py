"""Custom exceptions and error handling"""

from typing import Any, Optional

from fastapi import HTTPException, status


class APIException(Exception):
    """Base API exception"""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)


def raise_http_exception(
    status_code: int,
    message: str,
    headers: Optional[dict] = None,
) -> None:
    """Raise an HTTP exception with consistent format"""
    raise HTTPException(
        status_code=status_code,
        detail={"error": message},
        headers=headers,
    )


# Common exceptions
class NotFoundError(APIException):
    """Resource not found"""

    def __init__(self, resource: str = "Resource"):
        super().__init__(
            message=f"{resource} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class UnauthorizedError(APIException):
    """Authentication required"""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenError(APIException):
    """Access denied"""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class BadRequestError(APIException):
    """Bad request"""

    def __init__(self, message: str = "Bad request"):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class ConflictError(APIException):
    """Resource conflict"""

    def __init__(self, message: str = "Resource already exists"):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
        )


class RateLimitError(APIException):
    """Rate limit exceeded"""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


class StorageLimitError(APIException):
    """Storage limit exceeded"""

    def __init__(self, message: str = "Storage limit exceeded"):
        super().__init__(
            message=message,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )
