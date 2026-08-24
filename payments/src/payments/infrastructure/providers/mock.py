"""Deterministic provider used by offline tests."""

from __future__ import annotations

import uuid

from payments.application.contracts import ProviderPayment, ProviderRefund


class MockPaymentProvider:
    """Return deterministic test objects without making network requests."""

    async def create_payment(
        self,
        *,
        payment_id: uuid.UUID,
        order_id: uuid.UUID,
        amount: int,
        currency: str,
        description: str,
        return_url: str,
        idempotency_key: str,
    ) -> ProviderPayment:
        del description, return_url, idempotency_key
        external_id = f"mock-{payment_id}"
        return ProviderPayment(
            id=external_id,
            status="pending",
            amount=amount,
            currency=currency,
            test=True,
            metadata={"payment_id": str(payment_id), "order_id": str(order_id)},
            confirmation_url=f"https://example.test/payments/{external_id}",
        )

    async def get_payment(self, external_id: str) -> ProviderPayment:
        raise LookupError(f"Mock payment state was not registered: {external_id}")

    async def create_refund(
        self,
        *,
        payment: ProviderPayment,
        idempotency_key: str,
        reason: str,
    ) -> ProviderRefund:
        del idempotency_key, reason
        return ProviderRefund(
            id=f"mock-refund-{payment.id}",
            payment_id=payment.id,
            status="succeeded",
            amount=payment.amount,
            currency=payment.currency,
        )

    async def get_refund(self, external_id: str) -> ProviderRefund:
        raise LookupError(f"Mock refund state was not registered: {external_id}")
