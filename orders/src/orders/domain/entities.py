"""Domain value objects and enumerations."""

from __future__ import annotations

from enum import StrEnum


class OrderStatus(StrEnum):
    """Lifecycle status of an order."""

    PENDING = "PENDING"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    PAID = "PAID"
    CONFIRMED = "CONFIRMED"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    CANCELLED = "CANCELLED"


class OrderEventType(StrEnum):
    """Outbox event types published by the orders service."""

    ORDER_CREATED = "OrderCreated"
    PAYMENT_REQUESTED = "PaymentRequested"
    ORDER_CONFIRMED = "OrderConfirmed"
    ORDER_CANCELLED = "OrderCancelled"
