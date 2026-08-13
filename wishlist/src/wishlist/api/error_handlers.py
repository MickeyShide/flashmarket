"""Translate domain exceptions into JSON error responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from wishlist.domain.exceptions import (
    ItemAlreadyInWishlist,
    ItemNotInWishlist,
    WishlistError,
    WishlistLimitReached,
)

ERROR_STATUS: dict[type[WishlistError], int] = {
    ItemAlreadyInWishlist: status.HTTP_409_CONFLICT,
    ItemNotInWishlist: status.HTTP_404_NOT_FOUND,
    WishlistLimitReached: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


async def wishlist_error_handler(
    request: Request,
    exc: WishlistError,
) -> JSONResponse:
    """Map a WishlistError subclass to the appropriate HTTP status code."""
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
