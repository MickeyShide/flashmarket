"""Translate domain exceptions into JSON error responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from inventory.domain.exceptions import (
    InvalidReservationState,
    InventoryError,
    OutOfStock,
    ReservationNotFound,
    StockInvariantViolation,
    StockNotFound,
)

ERROR_STATUS: dict[type[InventoryError], int] = {
    StockNotFound: status.HTTP_404_NOT_FOUND,
    OutOfStock: status.HTTP_409_CONFLICT,
    ReservationNotFound: status.HTTP_404_NOT_FOUND,
    InvalidReservationState: status.HTTP_409_CONFLICT,
    StockInvariantViolation: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


async def inventory_error_handler(
    request: Request,
    exc: InventoryError,
) -> JSONResponse:
    """Map an InventoryError subclass to the appropriate HTTP status code."""
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
