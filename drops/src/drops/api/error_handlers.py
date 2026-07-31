"""Translate domain exceptions into JSON error responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from drops.domain.exceptions import (
    DropError,
    DropNotFound,
    DropTimeConflict,
    DuplicateDropSlug,
    InvalidDropState,
    ProductAlreadyInDrop,
)

ERROR_STATUS: dict[type[DropError], int] = {
    DropNotFound: status.HTTP_404_NOT_FOUND,
    InvalidDropState: status.HTTP_409_CONFLICT,
    DuplicateDropSlug: status.HTTP_409_CONFLICT,
    ProductAlreadyInDrop: status.HTTP_409_CONFLICT,
    DropTimeConflict: status.HTTP_422_UNPROCESSABLE_ENTITY,
}


async def drops_error_handler(
    request: Request,
    exc: DropError,
) -> JSONResponse:
    """Map a DropError subclass to the appropriate HTTP status code."""
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
