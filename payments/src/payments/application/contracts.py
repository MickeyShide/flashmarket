"""Provider-facing contracts for the payments application layer."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ProviderPayment:
    """Normalized payment returned by an external provider."""

    id: str
    status: str
    amount: int
    currency: str
    test: bool
    metadata: dict[str, str]
    confirmation_url: str | None = None
    cancellation_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderRefund:
    """Normalized refund returned by an external provider."""

    id: str
    payment_id: str
    status: str
    amount: int
    currency: str
    cancellation_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderPaymentPage:
    """Bounded page returned by the provider payment collection."""

    items: tuple[ProviderPayment, ...]
    next_cursor: str | None = None


@dataclass(frozen=True, slots=True)
class ProviderRefundPage:
    """Bounded page returned by the provider refund collection."""

    items: tuple[ProviderRefund, ...]
    next_cursor: str | None = None


class PaymentProvider(Protocol):
    """Operations needed by the payment lifecycle."""

    async def create_payment(
        self,
        *,
        payment_id: uuid.UUID,
        attempt_id: uuid.UUID,
        order_id: uuid.UUID,
        amount: int,
        currency: str,
        description: str,
        return_url: str,
        idempotency_key: str,
    ) -> ProviderPayment: ...

    async def get_payment(self, external_id: str) -> ProviderPayment: ...

    async def list_payments(
        self,
        *,
        created_gte: datetime,
        created_lte: datetime,
        limit: int,
        cursor: str | None = None,
    ) -> ProviderPaymentPage: ...

    async def create_refund(
        self,
        *,
        payment: ProviderPayment,
        amount: int,
        idempotency_key: str,
        reason: str,
    ) -> ProviderRefund: ...

    async def get_refund(self, external_id: str) -> ProviderRefund: ...

    async def list_refunds(
        self,
        *,
        created_gte: datetime,
        created_lte: datetime,
        payment_id: str,
        limit: int,
        cursor: str | None = None,
    ) -> ProviderRefundPage: ...
