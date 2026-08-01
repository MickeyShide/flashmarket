"""Domain value objects and state definitions."""

from dataclasses import dataclass
from enum import StrEnum


class AssetStatus(StrEnum):
    """Persistent asset lifecycle states."""

    PENDING = "PENDING"
    VERIFYING = "VERIFYING"
    READY = "READY"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    DELETING = "DELETING"
    DELETED = "DELETED"


class Visibility(StrEnum):
    """Asset visibility; v1 intentionally supports public only."""

    PUBLIC = "public"


@dataclass(frozen=True, slots=True)
class PresignedPost:
    """Browser-visible S3 form contract."""

    url: str
    fields: dict[str, str]


@dataclass(frozen=True, slots=True)
class StoredObject:
    """Metadata returned by S3 HEAD."""

    size: int
    content_type: str
    metadata: dict[str, str]


@dataclass(frozen=True, slots=True)
class ValidatedContent:
    """Trusted metadata extracted from stored bytes."""

    content_type: str
    sha256: str
    width: int | None = None
    height: int | None = None
