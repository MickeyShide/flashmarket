"""Translate domain exceptions into JSON error responses."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from catalog.domain.exceptions import (
    BrandNotFound,
    CatalogError,
    CategoryNotFound,
    DuplicateSKU,
    DuplicateSlug,
    DuplicateVariantOptions,
    InvalidProductData,
    ProductNotFound,
    VariantError,
    VariantNotFound,
)

ERROR_STATUS: dict[type[CatalogError], int] = {
    ProductNotFound: status.HTTP_404_NOT_FOUND,
    CategoryNotFound: status.HTTP_404_NOT_FOUND,
    BrandNotFound: status.HTTP_404_NOT_FOUND,
    VariantNotFound: status.HTTP_404_NOT_FOUND,
    DuplicateSlug: status.HTTP_409_CONFLICT,
    DuplicateSKU: status.HTTP_409_CONFLICT,
    DuplicateVariantOptions: status.HTTP_409_CONFLICT,
    InvalidProductData: status.HTTP_422_UNPROCESSABLE_CONTENT,
}


async def catalog_error_handler(
    request: Request,
    exc: CatalogError,
) -> JSONResponse:
    """Map a CatalogError subclass to the appropriate HTTP status code."""
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
