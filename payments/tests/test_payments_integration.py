"""Comprehensive integration tests for Payments microservice (PAY-001 through PAY-013)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payments.event_consumer import handle_payment_requested
from payments.infrastructure.models import OutboxEventModel
from payments.outbox_worker import publish_outbox_batch


@pytest.mark.asyncio
async def test_pay_001_to_006_payment_lifecycle_and_idempotency(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """PAY-001..PAY-006: Payment creation, confirm, fail, cancel, and idempotency."""
    order_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # 1. Create pending payment via API
    create_resp = await client.post(
        "/api/v1/payments",
        json={
            "order_id": str(order_id),
            "user_id": str(user_id),
            "amount": 9999,
            "currency": "RUB",
            "provider": "mock",
        },
    )
    assert create_resp.status_code == 201
    payment_data = create_resp.json()
    assert payment_data["status"] == "PENDING"
    payment_id = uuid.UUID(payment_data["id"])

    # 2. Duplicate create request returns existing payment (idempotency)
    dup_resp = await client.post(
        "/api/v1/payments",
        json={
            "order_id": str(order_id),
            "user_id": str(user_id),
            "amount": 9999,
            "currency": "RUB",
        },
    )
    assert dup_resp.status_code == 201
    assert dup_resp.json()["id"] == str(payment_id)

    # 3. Confirm payment -> SUCCESS
    confirm_resp = await client.post(f"/api/v1/payments/{payment_id}/confirm")
    assert confirm_resp.status_code == 200
    assert confirm_resp.json()["status"] == "SUCCESS"

    # 4. Confirm already successful payment -> 409
    dup_confirm = await client.post(f"/api/v1/payments/{payment_id}/confirm")
    assert dup_confirm.status_code == 409

    # 5. Create new payment to test fail flow
    order_id_2 = uuid.uuid4()
    p2_resp = await client.post(
        "/api/v1/payments",
        json={
            "order_id": str(order_id_2),
            "user_id": str(user_id),
            "amount": 4999,
        },
    )
    p2_id = uuid.UUID(p2_resp.json()["id"])

    fail_resp = await client.post(f"/api/v1/payments/{p2_id}/fail")
    assert fail_resp.status_code == 200
    assert fail_resp.json()["status"] == "FAILED"

    # 6. Create third payment to test cancel flow
    order_id_3 = uuid.uuid4()
    p3_resp = await client.post(
        "/api/v1/payments",
        json={
            "order_id": str(order_id_3),
            "user_id": str(user_id),
            "amount": 2999,
        },
    )
    p3_id = uuid.UUID(p3_resp.json()["id"])

    cancel_resp = await client.post(f"/api/v1/payments/{p3_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_pay_008_consumer_handle_payment_requested(
    session_factory: async_sessionmaker[AsyncSession], client: AsyncClient
) -> None:
    """PAY-008: Consumer handles orders.PaymentRequested event duplicate-safely."""
    order_id = uuid.uuid4()
    user_id = uuid.uuid4()
    payload = {
        "order_id": str(order_id),
        "user_id": str(user_id),
        "amount": 7500,
        "currency": "RUB",
    }

    async with session_factory() as session, session.begin():
        await handle_payment_requested(session, payload)

    # Verify payment created in PENDING
    list_resp = await client.get(f"/api/v1/payments/users/{user_id}")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["amount"] == 7500
    assert items[0]["status"] == "PENDING"

    # Redelivery of PaymentRequested should be ignored cleanly
    async with session_factory() as session, session.begin():
        await handle_payment_requested(session, payload)

    list_resp_2 = await client.get(f"/api/v1/payments/users/{user_id}")
    assert len(list_resp_2.json()["items"]) == 1


@pytest.mark.asyncio
async def test_pay_010_outbox_worker_retries(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """PAY-010: Outbox worker retries failed payment events."""
    async with session_factory() as session, session.begin():
        event = OutboxEventModel(
            event_type="PaymentSucceeded",
            payload='{"payment_id": "test"}',
            status="failed",
            attempts=1,
        )
        session.add(event)

    class MockExchange:
        def __init__(self) -> None:
            self.published = 0

        async def publish(self, message: any, routing_key: str, mandatory: bool = True) -> bool:
            self.published += 1
            return True

    mock_exchange = MockExchange()
    count = await publish_outbox_batch(mock_exchange, session_factory=session_factory)
    assert count >= 1
    assert mock_exchange.published >= 1


@pytest.mark.asyncio
async def test_pay_013_readiness_probe(client: AsyncClient) -> None:
    """PAY-013: Readiness probe returns HTTP 200."""
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
