"""Translate domain exceptions into JSON error responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from orders.domain.exceptions import (
    DuplicateOrder,
    DuplicatePromocodeCode,
    InvalidOrderState,
    OrderError,
    OrderNotFound,
    PromocodeAlreadyUsed,
    PromocodeDisabled,
    PromocodeError,
    PromocodeExpired,
    PromocodeLimitReached,
    PromocodeMinAmountNotMet,
    PromocodeNotFound,
)

ERROR_STATUS: dict[type[Exception], int] = {
    OrderNotFound: status.HTTP_404_NOT_FOUND,
    InvalidOrderState: status.HTTP_409_CONFLICT,
    DuplicateOrder: status.HTTP_409_CONFLICT,
    PromocodeNotFound: status.HTTP_404_NOT_FOUND,
    PromocodeExpired: status.HTTP_422_UNPROCESSABLE_ENTITY,
    PromocodeDisabled: status.HTTP_422_UNPROCESSABLE_ENTITY,
    PromocodeLimitReached: status.HTTP_422_UNPROCESSABLE_ENTITY,
    PromocodeAlreadyUsed: status.HTTP_409_CONFLICT,
    PromocodeMinAmountNotMet: status.HTTP_422_UNPROCESSABLE_ENTITY,
    DuplicatePromocodeCode: status.HTTP_409_CONFLICT,
}


async def order_error_handler(
    request: Request,
    exc: OrderError | PromocodeError,
) -> JSONResponse:
    """Map an OrderError or PromocodeError subclass to the appropriate HTTP status code."""
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
                "code": getattr(exc, "code", "error"),
                "message": getattr(exc, "public_message", str(exc)),
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )
