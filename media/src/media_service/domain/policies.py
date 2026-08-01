"""Purpose policies, authorization, filename handling, and byte validation."""

import hashlib
import re
import unicodedata
import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePath
from uuid import UUID

from PIL import Image, UnidentifiedImageError

from media_service.domain.entities import ValidatedContent
from media_service.domain.exceptions import (
    AssetAccessDenied,
    FileTooLarge,
    InvalidBinding,
    InvalidFilename,
    UnsupportedContentType,
    UnsupportedPurpose,
    UploadValidationFailed,
)

MIB = 1024 * 1024
ENTITY_TYPE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True, slots=True)
class MediaPolicy:
    """Rules for one public asset purpose."""

    purpose: str
    max_size: int
    content_types: frozenset[str]
    admin_only: bool
    required_entity_type: str | None
    entity_required: bool = True
    owner_entity: bool = False


IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})
DOCUMENT_TYPES = frozenset({"application/pdf"})

POLICIES: dict[str, MediaPolicy] = {
    "user_avatar": MediaPolicy("user_avatar", 5 * MIB, IMAGE_TYPES, False, "user", True, True),
    "product_image": MediaPolicy("product_image", 15 * MIB, IMAGE_TYPES, True, "product"),
    "brand_logo": MediaPolicy("brand_logo", 10 * MIB, IMAGE_TYPES, True, "brand"),
    "review_image": MediaPolicy("review_image", 10 * MIB, IMAGE_TYPES, False, "review", False),
    "drop_image": MediaPolicy("drop_image", 15 * MIB, IMAGE_TYPES, True, "drop"),
    "notification_attachment": MediaPolicy(
        "notification_attachment", 10 * MIB, IMAGE_TYPES | DOCUMENT_TYPES, True, "notification"
    ),
    "public_asset": MediaPolicy(
        "public_asset", 25 * MIB, IMAGE_TYPES | DOCUMENT_TYPES, True, None, False
    ),
}


def get_policy(purpose: str) -> MediaPolicy:
    """Return a registered policy or raise a stable domain error."""
    try:
        return POLICIES[purpose]
    except KeyError as exc:
        raise UnsupportedPurpose() from exc


def authorize_upload(
    *,
    policy: MediaPolicy,
    user_id: UUID,
    role: str,
    entity_type: str | None,
    entity_id: UUID | None,
) -> None:
    """Validate role and binding for a requested upload."""
    if policy.admin_only and role != "ADMIN":
        raise AssetAccessDenied()
    validate_binding(policy, entity_type, entity_id)
    if policy.owner_entity and role != "ADMIN" and entity_id != user_id:
        raise AssetAccessDenied()


def validate_binding(policy: MediaPolicy, entity_type: str | None, entity_id: UUID | None) -> None:
    """Validate binding shape against a purpose policy."""
    if (entity_type is None) != (entity_id is None):
        raise InvalidBinding()
    if policy.entity_required and entity_id is None:
        raise InvalidBinding()
    if entity_type is not None and not ENTITY_TYPE_PATTERN.fullmatch(entity_type):
        raise InvalidBinding()
    if policy.required_entity_type is not None and entity_type not in {
        None if not policy.entity_required else policy.required_entity_type,
        policy.required_entity_type,
    }:
        raise InvalidBinding()


def validate_declaration(policy: MediaPolicy, content_type: str, size: int) -> None:
    """Validate client-declared type and size before signing."""
    if content_type not in policy.content_types:
        raise UnsupportedContentType()
    if size < 1 or size > policy.max_size:
        raise FileTooLarge()


def sanitize_filename(filename: str) -> str:
    """Create a display-safe basename while preserving a useful extension."""
    if not filename or "\x00" in filename:
        raise InvalidFilename()
    normalized = unicodedata.normalize("NFKC", filename).replace("\\", "/")
    basename = PurePath(normalized).name.strip().strip(".")
    basename = SAFE_FILENAME_PATTERN.sub("-", basename).strip("-.")
    if not basename or basename in {".", ".."}:
        raise InvalidFilename()
    if len(basename) > 180:
        stem, dot, suffix = basename.rpartition(".")
        basename = f"{stem[:150]}.{suffix[:20]}" if dot else basename[:180]
    return basename


def detect_content_type(content: bytes) -> str:
    """Detect the small v1 allowlist from untrusted bytes."""
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    if content.startswith(b"%PDF-"):
        return "application/pdf"
    raise UnsupportedContentType()


def validate_content(content: bytes, declared_type: str, max_pixels: int) -> ValidatedContent:
    """Validate bytes, calculate a digest, and inspect raster dimensions."""
    detected = detect_content_type(content)
    if detected != declared_type:
        raise UnsupportedContentType()
    digest = hashlib.sha256(content).hexdigest()
    if detected == "application/pdf":
        if b"%%EOF" not in content[-2048:]:
            raise UploadValidationFailed()
        return ValidatedContent(content_type=detected, sha256=digest)

    formats = {
        "image/jpeg": ["JPEG"],
        "image/png": ["PNG"],
        "image/gif": ["GIF"],
        "image/webp": ["WEBP"],
    }[detected]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content), formats=formats) as image:
                width, height = image.size
                if width < 1 or height < 1 or width * height > max_pixels:
                    raise UploadValidationFailed("Image dimensions exceed the allowed limit")
                image.verify()
            with Image.open(BytesIO(content), formats=formats) as image:
                image.load()
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as exc:
        raise UploadValidationFailed() from exc
    return ValidatedContent(
        content_type=detected,
        sha256=digest,
        width=width,
        height=height,
    )
