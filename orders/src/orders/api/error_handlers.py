"""Translate domain exceptions into JSON error responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from orders.domain.exceptions import (
    DuplicateOrder,
    InvalidOrderState,
    OrderError,
    OrderNotFound,
)

ERROR_STATUS: dict[type[OrderError], int] = {
    OrderNotFound: status.HTTP_404_NOT_FOUND,
    InvalidOrderState: status.HTTP_409_CONFLICT,
    DuplicateOrder: status.HTTP_409_CONFLICT,
}


async def order_error_handler(
    request: Request,
    exc: OrderError,
) -> JSONResponse:
    """Map an OrderError subclass to the appropriate HTTP status code."""
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
