"""Hosted checkout, verified webhook, and refund tests."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from jwt_verifier.testing import TestKeyStore as JWTTestKeyStore
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from payments.api.dependencies import get_payment_provider
from payments.application.contracts import (
    ProviderPayment,
    ProviderPaymentPage,
    ProviderRefund,
    ProviderRefundPage,
)
from payments.application.services.payment import PaymentService
from payments.domain.entities import (
    PaymentAttemptStatus,
    PaymentStatus,
    ProviderOperationStatus,
    RefundStatus,
)
from payments.domain.exceptions import (
    InvalidPaymentState,
    PaymentProviderRejected,
    PaymentProviderResultUnknown,
    PaymentVerificationFailed,
)
from payments.event_consumer import handle_payment_requested
from payments.infrastructure.database import Base, utc_now
from payments.infrastructure.models import (
    OutboxEventModel,
    PaymentAttemptModel,
    ProviderOperationModel,
    RefundModel,
    WebhookInboxModel,
)
from payments.infrastructure.repositories.payment import OutboxRepository, PaymentRepository
from payments.main import app


class FakeProvider:
    """Stateful provider double whose GET result can be changed by a test."""

    def __init__(self) -> None:
        self.payments: dict[str, ProviderPayment] = {}
        self.refunds: dict[str, ProviderRefund] = {}
        self.create_calls = 0
        self.refund_calls = 0
        self.refund_cancellation_reason: str | None = None
        self.refund_amount_delta = 0
        self.refund_rejected = False
        self.refund_unknown_after_create = False

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
        del description, idempotency_key
        self.create_calls += 1
        external_id = f"yk-{attempt_id}"
        payment = ProviderPayment(
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
        amount: int,
        idempotency_key: str,
        reason: str,
    ) -> ProviderRefund:
        del reason
        self.refund_calls += 1
        if self.refund_rejected:
            raise PaymentProviderRejected
        refund = ProviderRefund(
            id=f"refund-{idempotency_key}",
            payment_id=payment.id,
            status="canceled" if self.refund_cancellation_reason else "succeeded",
            amount=amount + self.refund_amount_delta,
            currency=payment.currency,
            cancellation_reason=self.refund_cancellation_reason,
        )
        self.refunds[refund.id] = refund
        if self.refund_unknown_after_create:
            raise PaymentProviderResultUnknown
        return refund

    async def get_refund(self, external_id: str) -> ProviderRefund:
        return self.refunds[external_id]

    async def list_refunds(
        self,
        *,
        created_gte: datetime,
        created_lte: datetime,
        payment_id: str,
        limit: int,
        cursor: str | None = None,
    ) -> ProviderRefundPage:
        del created_gte, created_lte, cursor
        items = tuple(refund for refund in self.refunds.values() if refund.payment_id == payment_id)
        return ProviderRefundPage(items=items[:limit])


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


class MismatchedPaymentProvider(FakeProvider):
    """Return an object from POST that cannot be trusted as this payment."""

    async def create_payment(self, **kwargs: object) -> ProviderPayment:
        payment = await super().create_payment(**kwargs)  # type: ignore[arg-type]
        return replace(payment, amount=payment.amount + 1)


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


async def _process_webhooks(
    session_factory: async_sessionmaker[AsyncSession],
    provider: FakeProvider,
) -> int:
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
        return await service.process_webhook_inbox(limit=50)


async def _mark_payment_succeeded(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    provider: FakeProvider,
) -> uuid.UUID:
    app.dependency_overrides[get_payment_provider] = lambda: provider
    order_id, _ = await _authoritative_payment(session_factory)
    await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    external_id = next(reversed(provider.payments))
    provider.payments[external_id] = replace(provider.payments[external_id], status="succeeded")
    await client.post(
        "/api/v1/payments/webhooks/yookassa",
        json={
            "type": "notification",
            "event": "payment.succeeded",
            "object": {"id": external_id, "status": "succeeded"},
        },
    )
    await _process_webhooks(session_factory, provider)
    async with session_factory() as session:
        payment = await PaymentRepository(session).get_by_order_id(order_id)
        assert payment is not None
        return payment.id


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
    assert response.json()["status"] == "accepted"
    assert duplicate.json()["status"] == "duplicate"
    assert await _process_webhooks(session_factory, provider) == 1

    async with session_factory() as session:
        payment = await PaymentRepository(session).get_by_order_id(order_id)
        assert payment is not None
        assert payment.status == PaymentStatus.SUCCESS
        events = await session.scalars(
            select(OutboxEventModel).where(OutboxEventModel.event_type == "PaymentSucceeded")
        )
        assert len(events.all()) == 1


@pytest.mark.asyncio
async def test_concurrent_checkout_converges_on_one_active_attempt(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'payments.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    provider = FakeProvider()
    order_id, _ = await _authoritative_payment(session_factory)

    async def checkout() -> uuid.UUID | None:
        async with session_factory() as session:
            service = PaymentService(
                session=session,
                payment_repo=PaymentRepository(session),
                outbox_repo=OutboxRepository(session),
                provider=provider,
                provider_name="mock",
            )
            try:
                payment = await service.start_checkout(order_id)
            except PaymentProviderResultUnknown:
                payment = await service.get_payment_by_order_id(order_id)
            return payment.current_attempt_id

    first_attempt_id, second_attempt_id = await asyncio.gather(checkout(), checkout())
    assert first_attempt_id == second_attempt_id
    assert provider.create_calls == 1
    async with session_factory() as session:
        attempts = (await session.scalars(select(PaymentAttemptModel))).all()
        operations = (await session.scalars(select(ProviderOperationModel))).all()
        assert len(attempts) == len(operations) == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_expired_attempt_requires_provider_confirmation_before_retry(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = FakeProvider()
    app.dependency_overrides[get_payment_provider] = lambda: provider
    order_id, _ = await _authoritative_payment(session_factory)
    first = await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    first_attempt_id = first.json()["attempt_id"]

    async with session_factory() as session, session.begin():
        attempt = await session.get(PaymentAttemptModel, uuid.UUID(first_attempt_id))
        assert attempt is not None
        attempt.expires_at = utc_now() - timedelta(seconds=1)
        attempt.next_reconcile_at = utc_now() - timedelta(seconds=1)

    second = await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    assert second.status_code == 200
    assert second.json()["attempt_id"] == first_attempt_id
    assert provider.create_calls == 1
    external_id = next(iter(provider.payments))
    provider.payments[external_id] = replace(
        provider.payments[external_id],
        status="canceled",
        cancellation_reason="expired_on_confirmation",
    )
    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
            provider=provider,
            provider_name="yookassa",
        )
        assert await service.reconcile_active_attempts(limit=10) == 1

    third = await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    assert third.status_code == 200
    assert third.json()["attempt_id"] != first_attempt_id
    assert provider.create_calls == 2
    async with session_factory() as session:
        attempts = (
            await session.scalars(
                select(PaymentAttemptModel).order_by(PaymentAttemptModel.attempt_number)
            )
        ).all()
        assert [attempt.status for attempt in attempts] == ["CANCELED", "PENDING"]


@pytest.mark.asyncio
async def test_canceled_attempt_can_be_retried_without_new_order(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = FakeProvider()
    app.dependency_overrides[get_payment_provider] = lambda: provider
    order_id, _ = await _authoritative_payment(session_factory)
    first = await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    first_attempt_id = first.json()["attempt_id"]
    external_id = next(iter(provider.payments))
    provider.payments[external_id] = replace(
        provider.payments[external_id],
        status="canceled",
        cancellation_reason="payment_method_restricted",
    )
    await client.post(
        "/api/v1/payments/webhooks/yookassa",
        json={
            "type": "notification",
            "event": "payment.canceled",
            "object": {"id": external_id, "status": "canceled"},
        },
    )
    assert await _process_webhooks(session_factory, provider) == 1

    second = await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    assert second.status_code == 200
    assert second.json()["attempt_id"] != first_attempt_id
    assert provider.create_calls == 2
    async with session_factory() as session:
        payment = await PaymentRepository(session).get_by_order_id(order_id)
        attempts = (
            await session.scalars(
                select(PaymentAttemptModel).order_by(PaymentAttemptModel.attempt_number)
            )
        ).all()
        assert payment is not None
        assert payment.status == PaymentStatus.PENDING
        assert [attempt.status for attempt in attempts] == ["CANCELED", "PENDING"]


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
        attempt = await session.scalar(select(PaymentAttemptModel))
        payment = await PaymentRepository(session).get_by_order_id(order_id)
        assert operation is not None
        assert attempt is not None
        assert payment is not None
        assert operation.status == ProviderOperationStatus.QUARANTINED
        assert operation.last_error_code == "idempotency_expired:provider_payment_not_found"
        assert attempt.status == PaymentAttemptStatus.UNKNOWN
        assert attempt.next_reconcile_at is None
        assert payment.current_attempt_status == PaymentAttemptStatus.UNKNOWN
        assert provider.create_calls == 1

    retry = await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    assert retry.status_code == 202
    assert provider.create_calls == 1


@pytest.mark.asyncio
async def test_mismatched_successful_payment_response_blocks_second_post(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = MismatchedPaymentProvider()
    app.dependency_overrides[get_payment_provider] = lambda: provider
    order_id, _ = await _authoritative_payment(session_factory)

    first = await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    second = await client.post(f"/api/v1/payments/orders/{order_id}/checkout")

    assert first.status_code == 202
    assert second.status_code == 202
    assert provider.create_calls == 1
    async with session_factory() as session:
        operation = await session.scalar(select(ProviderOperationModel))
        attempt = await session.scalar(select(PaymentAttemptModel))
        assert operation is not None
        assert attempt is not None
        assert operation.status == ProviderOperationStatus.QUARANTINED
        assert operation.external_id is not None
        assert attempt.status == PaymentAttemptStatus.UNKNOWN
        assert attempt.cancellation_reason == "provider_verification_failed"


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
    assert response.status_code == 200
    assert await _process_webhooks(session_factory, provider) == 1

    async with session_factory() as session:
        payment = await PaymentRepository(session).get_by_order_id(order_id)
        assert payment is not None
        assert payment.status == PaymentStatus.PENDING
        inbox = await session.scalar(select(WebhookInboxModel))
        assert inbox is not None
        assert inbox.status == "QUARANTINED"
        assert inbox.last_error_code == "payment_verification_failed"


@pytest.mark.asyncio
async def test_malformed_webhook_is_durably_quarantined_and_acknowledged(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    response = await client.post(
        "/api/v1/payments/webhooks/yookassa",
        content=b"not-json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "acknowledged"
    async with session_factory() as session:
        inbox = await session.scalar(select(WebhookInboxModel))
        assert inbox is not None
        assert inbox.status == "QUARANTINED"
        assert inbox.last_error_code == "malformed_notification"


@pytest.mark.asyncio
async def test_out_of_order_webhooks_apply_current_provider_state_once(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = FakeProvider()
    app.dependency_overrides[get_payment_provider] = lambda: provider
    order_id, _ = await _authoritative_payment(session_factory)
    await client.post(f"/api/v1/payments/orders/{order_id}/checkout")
    external_id = next(iter(provider.payments))
    provider.payments[external_id] = replace(provider.payments[external_id], status="succeeded")

    canceled_hint = await client.post(
        "/api/v1/payments/webhooks/yookassa",
        json={
            "type": "notification",
            "event": "payment.canceled",
            "object": {"id": external_id, "status": "canceled"},
        },
    )
    succeeded_hint = await client.post(
        "/api/v1/payments/webhooks/yookassa",
        json={
            "type": "notification",
            "event": "payment.succeeded",
            "object": {"id": external_id, "status": "succeeded"},
        },
    )
    assert canceled_hint.status_code == succeeded_hint.status_code == 200
    assert await _process_webhooks(session_factory, provider) == 2

    async with session_factory() as session:
        payment = await PaymentRepository(session).get_by_order_id(order_id)
        events = (
            await session.scalars(
                select(OutboxEventModel).where(OutboxEventModel.event_type == "PaymentSucceeded")
            )
        ).all()
        assert payment is not None
        assert payment.status == PaymentStatus.SUCCESS
        assert len(events) == 1


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
    assert await _process_webhooks(session_factory, provider) == 1

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
async def test_partial_refunds_never_exceed_captured_amount(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = FakeProvider()
    payment_id = await _mark_payment_succeeded(client, session_factory, provider)

    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
            provider=provider,
            provider_name="yookassa",
        )
        partially_refunded = await service.refund_payment(
            payment_id,
            amount=4_000,
            request_id="partial-1",
        )
        assert partially_refunded.status == PaymentStatus.SUCCESS
        with pytest.raises(InvalidPaymentState):
            await service.refund_payment(
                payment_id,
                amount=10_000,
                request_id="too-much",
            )
        fully_refunded = await service.refund_payment(
            payment_id,
            amount=8_990,
            request_id="partial-2",
        )
        assert fully_refunded.status == PaymentStatus.REFUNDED

    async with session_factory() as session:
        refunds = (await session.scalars(select(RefundModel))).all()
        assert len(refunds) == 2
        assert sum(refund.amount for refund in refunds) == 12_990
        assert all(refund.status == RefundStatus.SUCCEEDED for refund in refunds)


@pytest.mark.asyncio
async def test_unknown_refund_is_recovered_by_bounded_list_without_second_post(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = FakeProvider()
    payment_id = await _mark_payment_succeeded(client, session_factory, provider)
    provider.refund_unknown_after_create = True
    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
            provider=provider,
            provider_name="yookassa",
        )
        with pytest.raises(PaymentProviderResultUnknown):
            await service.refund_payment(payment_id, request_id="uncertain-refund")
    provider.refund_unknown_after_create = False
    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
            provider=provider,
            provider_name="yookassa",
        )
        assert await service.reconcile_refunds(limit=10) == 1
    async with session_factory() as session:
        refund = await session.scalar(select(RefundModel))
        payment = await PaymentRepository(session).get_by_id(payment_id)
        assert refund is not None
        assert refund.status == RefundStatus.SUCCEEDED
        assert payment is not None
        assert payment.status == PaymentStatus.REFUNDED
        assert provider.refund_calls == 1


@pytest.mark.asyncio
async def test_aged_unknown_refund_keeps_balance_reserved_without_second_post(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = FakeProvider()
    payment_id = await _mark_payment_succeeded(client, session_factory, provider)
    provider.refund_unknown_after_create = True
    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
            provider=provider,
            provider_name="yookassa",
        )
        with pytest.raises(PaymentProviderResultUnknown):
            await service.refund_payment(payment_id, request_id="lost-refund")

    # Absence from a bounded provider listing is deliberately not treated as proof
    # that the refund POST failed.
    provider.refund_unknown_after_create = False
    provider.refunds.clear()
    async with session_factory() as session, session.begin():
        operation = await session.scalar(
            select(ProviderOperationModel).where(
                ProviderOperationModel.operation_type == "create_refund"
            )
        )
        assert operation is not None
        operation.first_requested_at = utc_now() - timedelta(hours=25)

    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
            provider=provider,
            provider_name="yookassa",
        )
        assert await service.reconcile_refunds(limit=10) == 1
        with pytest.raises(InvalidPaymentState):
            await service.refund_payment(payment_id, request_id="second-refund")

    async with session_factory() as session:
        refund = await session.scalar(select(RefundModel))
        assert refund is not None
        assert refund.status == RefundStatus.QUARANTINED
        assert refund.funds_reserved is True
        assert refund.cancellation_reason == "idempotency_expired:refund_not_found"
        assert provider.refund_calls == 1


@pytest.mark.asyncio
async def test_mismatched_successful_refund_response_keeps_balance_reserved(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = FakeProvider()
    payment_id = await _mark_payment_succeeded(client, session_factory, provider)
    provider.refund_amount_delta = 1
    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
            provider=provider,
            provider_name="yookassa",
        )
        with pytest.raises(PaymentVerificationFailed):
            await service.refund_payment(payment_id, request_id="mismatched-refund")
        with pytest.raises(InvalidPaymentState):
            await service.refund_payment(payment_id, request_id="second-refund")

    async with session_factory() as session:
        refund = await session.scalar(select(RefundModel))
        operation = await session.scalar(
            select(ProviderOperationModel).where(
                ProviderOperationModel.operation_type == "create_refund"
            )
        )
        assert refund is not None
        assert operation is not None
        assert refund.status == RefundStatus.QUARANTINED
        assert refund.funds_reserved is True
        assert refund.cancellation_reason == "provider_verification_failed"
        assert operation.status == ProviderOperationStatus.QUARANTINED
        assert provider.refund_calls == 1


@pytest.mark.asyncio
async def test_definite_refund_rejection_releases_balance_for_explicit_retry(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    provider = FakeProvider()
    payment_id = await _mark_payment_succeeded(client, session_factory, provider)
    provider.refund_rejected = True
    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
            provider=provider,
            provider_name="yookassa",
        )
        with pytest.raises(PaymentProviderRejected):
            await service.refund_payment(payment_id, request_id="rejected-refund")
        provider.refund_rejected = False
        payment = await service.refund_payment(payment_id, request_id="explicit-retry")
        assert payment.status == PaymentStatus.REFUNDED

    async with session_factory() as session:
        refunds = (
            await session.scalars(select(RefundModel).order_by(RefundModel.created_at))
        ).all()
        assert len(refunds) == 2
        assert refunds[0].status == RefundStatus.QUARANTINED
        assert refunds[0].funds_reserved is False
        assert refunds[1].status == RefundStatus.SUCCEEDED
        assert refunds[1].funds_reserved is True
        assert provider.refund_calls == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("reason", "expected_status"),
    [
        ("rejected_by_timeout", RefundStatus.CANCELED),
        ("insufficient_funds", RefundStatus.QUARANTINED),
        ("rejected_by_payee", RefundStatus.QUARANTINED),
        ("general_decline", RefundStatus.QUARANTINED),
    ],
)
async def test_refund_cancellation_policy_stops_blind_retries(
    client: AsyncClient,
    session_factory: async_sessionmaker[AsyncSession],
    reason: str,
    expected_status: RefundStatus,
) -> None:
    provider = FakeProvider()
    payment_id = await _mark_payment_succeeded(client, session_factory, provider)
    provider.refund_cancellation_reason = reason
    async with session_factory() as session:
        service = PaymentService(
            session=session,
            payment_repo=PaymentRepository(session),
            outbox_repo=OutboxRepository(session),
            provider=provider,
            provider_name="yookassa",
        )
        payment = await service.refund_payment(payment_id, request_id=f"policy-{reason}")
        assert payment.status == PaymentStatus.SUCCESS
    async with session_factory() as session:
        refund = await session.scalar(select(RefundModel))
        assert refund is not None
        assert refund.status == expected_status
        assert refund.funds_reserved is False
        assert (refund.next_attempt_at is not None) == (reason == "rejected_by_timeout")
        assert provider.refund_calls == 1

    if reason == "rejected_by_timeout":
        async with session_factory() as session, session.begin():
            refund = await session.scalar(select(RefundModel))
            assert refund is not None
            refund.next_attempt_at = utc_now() - timedelta(seconds=1)
        provider.refund_cancellation_reason = None
        async with session_factory() as session:
            service = PaymentService(
                session=session,
                payment_repo=PaymentRepository(session),
                outbox_repo=OutboxRepository(session),
                provider=provider,
                provider_name="yookassa",
            )
            assert await service.reconcile_refunds(limit=10) == 1
        async with session_factory() as session:
            refunds = (
                await session.scalars(select(RefundModel).order_by(RefundModel.created_at))
            ).all()
            payment = await PaymentRepository(session).get_by_id(payment_id)
            assert len(refunds) == 2
            assert refunds[0].funds_reserved is False
            assert refunds[1].status == RefundStatus.SUCCEEDED
            assert refunds[1].funds_reserved is True
            assert payment is not None
            assert payment.status == PaymentStatus.REFUNDED
            assert provider.refund_calls == 2


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
