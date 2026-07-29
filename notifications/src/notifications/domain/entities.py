"""Notification domain entities and enumerations."""

from __future__ import annotations

from enum import StrEnum


class NotificationChannel(StrEnum):
    """Supported notification channels."""

    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"


class NotificationStatus(StrEnum):
    """Lifecycle states of a notification."""

    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationEventType(StrEnum):
    """Outbox event types emitted by the Notifications service."""

    NOTIFICATION_SENT = "NotificationSent"
