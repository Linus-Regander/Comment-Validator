"""Application exceptions and their HTTP status-code mapping."""

from fastapi import Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    """Base class for expected application errors."""


class CommentNotFoundError(APIError):
    """Raised when a requested comment does not exist."""

    def __init__(self, comment_id: str) -> None:
        super().__init__(f"Comment '{comment_id}' not found")


class AuthenticationError(APIError):
    """Raised when a request has no valid Entra access token."""


class AuthenticationUnavailableError(APIError):
    """Raised when authentication configuration or key discovery is unavailable."""


class CommentForbiddenError(APIError):
    """Raised when a caller attempts to change another user's comment."""


class PiiDetectedError(APIError):
    """Raised when Azure detects personal or sensitive information."""

    def __init__(self) -> None:
        super().__init__("Comment contains personal or sensitive information")


class PiiScreeningUnavailableError(APIError):
    """Raised when the required Azure PII screening service cannot be used."""


ERROR_STATUS_CODES: dict[type[APIError], int] = {
    CommentNotFoundError: 404,
    AuthenticationError: 401,
    AuthenticationUnavailableError: 503,
    CommentForbiddenError: 403,
    PiiDetectedError: 422,
    PiiScreeningUnavailableError: 503,
}


async def api_error_handler(_: Request, error: APIError) -> JSONResponse:
    """Convert a known application exception to a stable JSON response."""
    status_code = next(
        (
            ERROR_STATUS_CODES[error_type]
            for error_type in type(error).__mro__
            if error_type in ERROR_STATUS_CODES
        ),
        500,
    )
    detail = str(error) if status_code != 500 else "Internal server error"
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers=headers,
    )