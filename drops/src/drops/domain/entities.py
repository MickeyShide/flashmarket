"""Domain entities and enums for the drops bounded context."""

from enum import StrEnum


class DropStatus(StrEnum):
    """Lifecycle status of a flash-sale drop."""

    DRAFT = "DRAFT"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    CANCELLED = "CANCELLED"


class DropEventType(StrEnum):
    """Outbox event types published by the drops service."""

    DROP_SCHEDULED = "DropScheduled"
    DROP_STARTED = "DropStarted"
    DROP_ENDED = "DropEnded"
    DROP_CANCELLED = "DropCancelled"
