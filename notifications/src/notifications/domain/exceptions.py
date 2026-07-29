"""Domain-level exceptions for the notifications bounded context."""


class NotificationError(Exception):
    """Base exception for all notifications domain errors."""

    code = "notification_error"
    message = "The operation could not be completed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.message)
        self.public_message = message or self.message


class NotificationNotFound(NotificationError):
    """Raised when a notification cannot be located."""

    code = "notification_not_found"
    message = "Notification not found"


class InvalidNotificationState(NotificationError):
    """Raised when a notification transition is not allowed."""

    code = "invalid_notification_state"
    message = "Invalid notification state"


class DeliveryFailed(NotificationError):
    """Raised when notification delivery fails."""

    code = "delivery_failed"
    message = "Failed to deliver notification"
