"""Payment domain entities and enumerations."""

from __future__ import annotations

from enum import StrEnum


class PaymentStatus(StrEnum):
    """Lifecycle states of a payment attempt."""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentEventType(StrEnum):
    """Outbox event types emitted by the Payments service."""

    PAYMENT_SUCCEEDED = "PaymentSucceeded"
    PAYMENT_FAILED = "PaymentFailed"
    PAYMENT_CANCELLED = "PaymentCancelled"
