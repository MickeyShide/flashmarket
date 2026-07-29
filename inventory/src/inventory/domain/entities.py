"""Domain value objects and enumerations."""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID


class ReservationStatus(StrEnum):
    """Lifecycle status of a stock reservation."""

    RESERVED = "RESERVED"
    COMMITTED = "COMMITTED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class InventoryEventType(StrEnum):
    """Outbox event types published by the inventory service."""

    INVENTORY_RESERVED = "InventoryReserved"
    RESERVATION_RELEASED = "ReservationReleased"
    INVENTORY_COMMITTED = "InventoryCommitted"


type ProductId = UUID
