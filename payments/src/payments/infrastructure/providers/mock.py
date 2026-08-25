"""Deterministic provider used by offline tests."""

from __future__ import annotations

import uuid
from datetime import datetime

from payments.application.contracts import (
    ProviderPayment,
    ProviderPaymentPage,
    ProviderRefund,
    ProviderRefundPage,
)


class MockPaymentProvider:
    """Return deterministic test objects without making network requests."""

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
    ) -> ProviderPayment:
        del description, return_url, idempotency_key
        external_id = f"mock-{attempt_id}"
        return ProviderPayment(
            id=external_id,
            status="pending",
            amount=amount,
            currency=currency,
            test=True,
            metadata={
                "payment_id": str(payment_id),
                "attempt_id": str(attempt_id),
                "order_id": str(order_id),
            },
            confirmation_url=f"https://example.test/payments/{external_id}",
        )

    async def get_payment(self, external_id: str) -> ProviderPayment:
        raise LookupError(f"Mock payment state was not registered: {external_id}")

    async def list_payments(
        self,
        *,
        created_gte: datetime,
        created_lte: datetime,
        limit: int,
        cursor: str | None = None,
    ) -> ProviderPaymentPage:
        del created_gte, created_lte, limit, cursor
        return ProviderPaymentPage(items=())

    async def create_refund(
        self,
        *,
        payment: ProviderPayment,
        amount: int,
        idempotency_key: str,
        reason: str,
    ) -> ProviderRefund:
        del idempotency_key, reason
        return ProviderRefund(
            id=f"mock-refund-{payment.id}",
            payment_id=payment.id,
            status="succeeded",
            amount=amount,
            currency=payment.currency,
        )

    async def get_refund(self, external_id: str) -> ProviderRefund:
        raise LookupError(f"Mock refund state was not registered: {external_id}")

    async def list_refunds(
        self,
        *,
        created_gte: datetime,
        created_lte: datetime,
        payment_id: str,
        limit: int,
        cursor: str | None = None,
    ) -> ProviderRefundPage:
        del created_gte, created_lte, payment_id, limit, cursor
        return ProviderRefundPage(items=())
