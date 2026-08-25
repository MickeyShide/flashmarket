"""Payment domain entities and enumerations."""

from __future__ import annotations

from enum import StrEnum


class PaymentStatus(StrEnum):
    """Lifecycle states of a payment attempt."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentEventType(StrEnum):
    """Outbox event types emitted by the Payments service."""

    PAYMENT_SUCCEEDED = "PaymentSucceeded"
    PAYMENT_FAILED = "PaymentFailed"
    PAYMENT_CANCELLED = "PaymentCancelled"
    PAYMENT_REFUNDED = "PaymentRefunded"


class ProviderOperationStatus(StrEnum):
    """Durable lifecycle of a financial provider write."""

    NEW = "NEW"
    IN_FLIGHT = "IN_FLIGHT"
    UNKNOWN = "UNKNOWN"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"


class WebhookInboxStatus(StrEnum):
    """Durable lifecycle of an accepted provider notification."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RETRY = "RETRY"
    PROCESSED = "PROCESSED"
    QUARANTINED = "QUARANTINED"


class PaymentAttemptStatus(StrEnum):
    """Lifecycle of one concrete attempt to pay an order."""

    NEW = "NEW"
    PREPARING = "PREPARING"
    UNKNOWN = "UNKNOWN"
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
