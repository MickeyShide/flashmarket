"""Hosted checkout, verified webhook, and refund tests."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from jwt_verifier.testing import TestKeyStore as JWTTestKeyStore
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payments.api.dependencies import get_payment_provider
from payments.application.contracts import ProviderPayment, ProviderPaymentPage, ProviderRefund
from payments.application.services.payment import PaymentService
from payments.domain.entities import PaymentStatus, ProviderOperationStatus
from payments.domain.exceptions import PaymentProviderResultUnknown
from payments.event_consumer import handle_payment_requested
from payments.infrastructure.database import utc_now
from payments.infrastructure.models import OutboxEventModel, ProviderOperationModel
from payments.infrastructure.repositories.payment import OutboxRepository, PaymentRepository
from payments.main import app


class FakeProvider:
    """Stateful provider double whose GET result can be changed by a test."""

    def __init__(self) -> None:
        self.payments: dict[str, ProviderPayment] = {}
        self.refunds: dict[str, ProviderRefund] = {}
        self.create_calls = 0
        self.refund_calls = 0

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
        del description, idempotency_key
        self.create_calls += 1
        external_id = f"yk-{payment_id}"
        payment = ProviderPayment(
            id=external_id,
            status="pending",
            amount=amount,
            currency=currency,
            test=True,
            metadata={"payment_id": str(payment_id), "order_id": str(order_id)},
            confirmation_url=f"https://yoomoney.test/confirm/{external_id}?back={return_url}",
        )
        self.payments[external_id] = payment
        return payment

    async def get_payment(self, external_id: str) -> ProviderPayment:
        return self.payments[external_id]

    async def list_payments(
        self,
        *,
        created_gte: datetime,
        created_lte: datetime,
        limit: int,
        cursor: str | None = None,
    ) -> ProviderPaymentPage:
        del created_gte, created_lte, cursor
        return ProviderPaymentPage(items=tuple(self.payments.values())[:limit])

    async def create_refund(
        self,
        *,
        payment: ProviderPayment,
        idempotency_key: str,
        reason: str,
    ) -> ProviderRefund:
        del idempotency_key, reason
        self.refund_calls += 1
        refund = ProviderRefund(
            id=f"refund-{payment.id}",
            payment_id=payment.id,
            status="succeeded",
            amount=payment.amount,
            currency=payment.currency,
        )
        self.refunds[refund.id] = refund
        return refund

    async def get_refund(self, external_id: str) -> ProviderRefund:
        return self.refunds[external_id]


class UnknownAfterCreateProvider(FakeProvider):
    """Simulate a timeout after YooKassa durably created the payment."""

    async def create_payment(self, **kwargs: object) -> ProviderPayment:
        await super().create_payment(**kwargs)  # type: ignore[arg-type]
        raise PaymentProviderResultUnknown


class UnknownWithoutCreateProvider(FakeProvider):
    async def create_payment(self, **kwargs: object) -> ProviderPayment:
        del kwargs
        self.create_calls += 1
        raise PaymentProviderResultUnknown


async def _authoritative_payment(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[uuid.UUID, uuid.UUID]:
    order_id = uuid.uuid4()
    user_id = uuid.uuid4()
    async with session_factory() as session, session.begin():
        await handle_payment_requested(
            session,
            {
                "order_id": str(order_id),
                "user_id": str(user_id),
                "amount": 12_990,
                "currency": "RUB",
            },
        )
    return order_id, user_id


@pytest.mark.asyncio
async def test_checkout_is_idempotent_and_webhook_is_verified(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = FakeProvider()
    app.dependency_overrides[get_payment_provider] = lambda: provider
    order_id, _ = await _authoritative_payment(session_factory)

    first = await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    second = await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert provider.create_calls == 1
    assert f"order_id={order_id}" in first.json()["confirmation_url"]

    external_id = next(iter(provider.payments))
    provider.payments[external_id] = replace(provider.payments[external_id], status="succeeded")
    notification = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": external_id, "status": "succeeded"},
    }
    response = await client.post("/api/v1/payments/webhooks/yookassa", json=notification)
    duplicate = await client.post("/api/v1/payments/webhooks/yookassa", json=notification)
    assert response.status_code == 200
    assert duplicate.status_code == 200

    async with session_factory() as session:
        payment = await PaymentRepository(session).get_by_order_id(order_id)
        assert payment is not None
        assert payment.status == PaymentStatus.SUCCESS
        events = await session.scalars(
            select(OutboxEventModel).where(OutboxEventModel.event_type == "PaymentSucceeded")
        )
        assert len(events.all()) == 1


@pytest.mark.asyncio
async def test_unknown_checkout_is_durable_and_never_blindly_reposted(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = UnknownAfterCreateProvider()
    app.dependency_overrides[get_payment_provider] = lambda: provider
    order_id, _ = await _authoritative_payment(session_factory)

    first = await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    second = await client.post(f"/api/v1/payments/orders/{order_id}/checkout")

    assert first.status_code == 202
    assert first.headers["retry-after"] == "2"
    assert first.json()["preparation_status"] == "pending"
    assert second.status_code == 202
    assert provider.create_calls == 1

    async with session_factory() as session:
        operation = await session.scalar(select(ProviderOperationModel))
        assert operation is not None
        assert operation.status == ProviderOperationStatus.UNKNOWN
        assert operation.attempt_count == 1
        assert operation.request_hash
        assert operation.idempotency_key.startswith("payment-")

    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
            provider=provider,
            provider_name="yookassa",
            return_url="https://shop.test/payment/return",
            test_mode_required=True,
        )
        assert await service.reconcile_unknown_operations(limit=10) == 1

    async with session_factory() as session:
        operation = await session.scalar(select(ProviderOperationModel))
        payment = await PaymentRepository(session).get_by_order_id(order_id)
        assert operation is not None
        assert operation.status == ProviderOperationStatus.SUCCEEDED
        assert payment is not None
        assert payment.external_id == operation.external_id


@pytest.mark.asyncio
async def test_unknown_operation_is_quarantined_after_idempotency_window(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = UnknownWithoutCreateProvider()
    app.dependency_overrides[get_payment_provider] = lambda: provider
    order_id, _ = await _authoritative_payment(session_factory)
    assert (await client.post(f"/api/v1/payments/orders/{order_id}/checkout")).status_code == 202

    async with session_factory() as session, session.begin():
        operation = await session.scalar(select(ProviderOperationModel))
        assert operation is not None
        operation.first_requested_at = utc_now() - timedelta(hours=25)

    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
            provider=provider,
            provider_name="yookassa",
            return_url="https://shop.test/payment/return",
            test_mode_required=True,
        )
        assert await service.reconcile_unknown_operations(limit=10) == 1

    async with session_factory() as session:
        operation = await session.scalar(select(ProviderOperationModel))
        assert operation is not None
        assert operation.status == ProviderOperationStatus.QUARANTINED
        assert operation.last_error_code == "idempotency_expired:provider_payment_not_found"
        assert provider.create_calls == 1


@pytest.mark.asyncio
async def test_webhook_rejects_provider_amount_mismatch(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = FakeProvider()
    app.dependency_overrides[get_payment_provider] = lambda: provider
    order_id, _ = await _authoritative_payment(session_factory)
    await client.post(f"/api/v1/payments/orders/{order_id}/checkout")

    external_id = next(iter(provider.payments))
    provider.payments[external_id] = replace(
        provider.payments[external_id],
        status="succeeded",
        amount=1,
    )
    response = await client.post(
        "/api/v1/payments/webhooks/yookassa",
        json={
            "type": "notification",
            "event": "payment.succeeded",
            "object": {"id": external_id},
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "payment_verification_failed"

    async with session_factory() as session:
        payment = await PaymentRepository(session).get_by_order_id(order_id)
        assert payment is not None
        assert payment.status == PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_full_refund_changes_state_only_after_provider_success(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = FakeProvider()
    app.dependency_overrides[get_payment_provider] = lambda: provider
    order_id, _ = await _authoritative_payment(session_factory)
    await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    external_id = next(iter(provider.payments))
    provider.payments[external_id] = replace(provider.payments[external_id], status="succeeded")
    await client.post(
        "/api/v1/payments/webhooks/yookassa",
        json={
            "type": "notification",
            "event": "payment.succeeded",
            "object": {"id": external_id},
        },
    )

    async with session_factory() as session:
        payment = await PaymentRepository(session).get_by_order_id(order_id)
        assert payment is not None
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
            provider=provider,
            provider_name="yookassa",
            return_url="https://shop.test/payment/return",
            test_mode_required=True,
        )
        refunded = await service.refund_payment(payment.id)
        assert refunded.status == PaymentStatus.REFUNDED
        assert refunded.refund_status == "succeeded"
        assert provider.refund_calls == 1


@pytest.mark.asyncio
async def test_checkout_requires_authoritative_payment(client: AsyncClient) -> None:
    response = await client.post(f"/api/v1/payments/orders/{uuid.uuid4()}/checkout")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "payment_not_ready"


@pytest.mark.asyncio
async def test_checkout_allows_only_the_payment_owner(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    jwt_keystore: JWTTestKeyStore,
) -> None:
    provider = FakeProvider()
    app.dependency_overrides[get_payment_provider] = lambda: provider
    order_id, user_id = await _authoritative_payment(session_factory)

    owner_token = jwt_keystore.create_token(user_id=user_id, role="CUSTOMER")
    owner = await client.post(
        f"/api/v1/payments/orders/{order_id}/checkout",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert owner.status_code == 200

    stranger_token = jwt_keystore.create_token(role="CUSTOMER")
    stranger = await client.post(
        f"/api/v1/payments/orders/{order_id}/checkout",
        headers={"Authorization": f"Bearer {stranger_token}"},
    )
    assert stranger.status_code == 403
