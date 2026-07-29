"""Translate domain exceptions into JSON error responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from notifications.domain.exceptions import (
    InvalidNotificationState,
    NotificationError,
    NotificationNotFound,
)

ERROR_STATUS: dict[type[NotificationError], int] = {
    NotificationNotFound: status.HTTP_404_NOT_FOUND,
    InvalidNotificationState: status.HTTP_409_CONFLICT,
}


async def notification_error_handler(
    request: Request,
    exc: NotificationError,
) -> JSONResponse:
    """Map a NotificationError subclass to the appropriate HTTP status code."""
    status_code = next(
        (
            error_status
            for error_type, error_status in ERROR_STATUS.items()
            if isinstance(exc, error_type)
        ),
        status.HTTP_400_BAD_REQUEST,
    )
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.public_message,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )
