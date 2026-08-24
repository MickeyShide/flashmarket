"""Translate domain exceptions into JSON error responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from payments.domain.exceptions import (
    InvalidPaymentState,
    PaymentError,
    PaymentNotFound,
    PaymentNotReady,
    PaymentProviderRejected,
    PaymentProviderUnavailable,
    PaymentVerificationFailed,
)

ERROR_STATUS: dict[type[PaymentError], int] = {
    PaymentNotFound: status.HTTP_404_NOT_FOUND,
    PaymentNotReady: status.HTTP_409_CONFLICT,
    InvalidPaymentState: status.HTTP_409_CONFLICT,
    PaymentProviderUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    PaymentProviderRejected: status.HTTP_502_BAD_GATEWAY,
    PaymentVerificationFailed: status.HTTP_409_CONFLICT,
}


async def payment_error_handler(
    request: Request,
    exc: PaymentError,
) -> JSONResponse:
    """Map a PaymentError subclass to the appropriate HTTP status code."""
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
