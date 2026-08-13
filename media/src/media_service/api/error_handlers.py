"""Translate Media domain exceptions to stable HTTP errors."""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from media_service.domain.exceptions import (
    AssetAccessDenied,
    AssetNotFound,
    FileTooLarge,
    InvalidAssetState,
    InvalidBinding,
    InvalidFilename,
    MediaCapacityExhausted,
    MediaError,
    MediaQuotaExceeded,
    StorageObjectNotFound,
    StorageUnavailable,
    UnsupportedContentType,
    UnsupportedPurpose,
    UploadExpired,
    UploadValidationFailed,
)

ERROR_STATUS: dict[type[MediaError], int] = {
    AssetNotFound: status.HTTP_404_NOT_FOUND,
    StorageObjectNotFound: status.HTTP_404_NOT_FOUND,
    AssetAccessDenied: status.HTTP_403_FORBIDDEN,
    InvalidAssetState: status.HTTP_409_CONFLICT,
    UploadExpired: status.HTTP_410_GONE,
    MediaQuotaExceeded: status.HTTP_422_UNPROCESSABLE_CONTENT,
    FileTooLarge: status.HTTP_413_CONTENT_TOO_LARGE,
    UnsupportedPurpose: status.HTTP_422_UNPROCESSABLE_CONTENT,
    UnsupportedContentType: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidBinding: status.HTTP_422_UNPROCESSABLE_CONTENT,
    InvalidFilename: status.HTTP_422_UNPROCESSABLE_CONTENT,
    UploadValidationFailed: status.HTTP_422_UNPROCESSABLE_CONTENT,
    StorageUnavailable: status.HTTP_503_SERVICE_UNAVAILABLE,
    MediaCapacityExhausted: status.HTTP_503_SERVICE_UNAVAILABLE,
}


async def media_error_handler(request: Request, exc: MediaError) -> JSONResponse:
    """Map domain errors without exposing provider details."""
    status_code = next(
        (value for error_type, value in ERROR_STATUS.items() if isinstance(exc, error_type)),
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
