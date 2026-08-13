"""Domain exceptions for Media."""


class MediaError(Exception):
    """Base public Media error."""

    code = "media_error"
    message = "The media operation could not be completed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.public_message = message or self.message


class AssetNotFound(MediaError):
    code = "asset_not_found"
    message = "Media asset was not found"


class AssetAccessDenied(MediaError):
    code = "asset_access_denied"
    message = "You cannot perform this media operation"


class InvalidAssetState(MediaError):
    code = "invalid_asset_state"
    message = "Media asset is not in a valid state for this operation"


class UnsupportedPurpose(MediaError):
    code = "unsupported_media_purpose"
    message = "Unsupported media purpose"


class UnsupportedContentType(MediaError):
    code = "unsupported_content_type"
    message = "Unsupported or mismatched file type"


class InvalidFilename(MediaError):
    code = "invalid_filename"
    message = "Invalid filename"


class FileTooLarge(MediaError):
    code = "file_too_large"
    message = "File exceeds the allowed size"


class InvalidBinding(MediaError):
    code = "invalid_media_binding"
    message = "Invalid media entity binding"


class UploadExpired(MediaError):
    code = "upload_expired"
    message = "Upload session has expired"


class UploadValidationFailed(MediaError):
    code = "upload_validation_failed"
    message = "Uploaded object failed validation"


class MediaQuotaExceeded(MediaError):
    code = "media_quota_exceeded"
    message = "Media quota has been exceeded"


class StorageUnavailable(MediaError):
    code = "media_storage_unavailable"
    message = "Media storage is temporarily unavailable"


class MediaCapacityExhausted(MediaError):
    code = "media_capacity_exhausted"
    message = "Media validation capacity is temporarily exhausted"


class StorageObjectNotFound(MediaError):
    code = "uploaded_object_not_found"
    message = "Uploaded object was not found"
