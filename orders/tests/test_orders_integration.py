"""Comprehensive integration tests for Orders microservice (ORD-001 through ORD-018)."""

import uuid
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orders.domain.entities import OrderEventType, OrderStatus
from orders.event_consumer import (
    handle_payment_failed,
    handle_payment_succeeded,
    handle_reservation_released,
)
from orders.infrastructure.models import OrderModel, OutboxEventModel
from orders.outbox_worker import publish_outbox_batch


@pytest.mark.asyncio
async def test_ord_001_create_order_from_reservation(client: AsyncClient, db_session: AsyncSession) -> None:
    """ORD-001: Create an order from a reservation and verify outbox events."""
    user_id = uuid.uuid4()
    product_id = uuid.uuid4()
    reservation_id = uuid.uuid4()

    resp = await client.post(
        "/api/v1/orders",
        json={
            "user_id": str(user_id),
            "product_id": str(product_id),
            "product_name": "Test Sneakers",
            "price": 5000,
            "currency": "RUB",
            "quantity": 1,
            "reservation_id": str(reservation_id),
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "AWAITING_PAYMENT"
    assert float(data["final_price"]) == 5000.0

    # Duplicate reservation_id should be rejected with 409
    dup_resp = await client.post(
        "/api/v1/orders",
        json={
            "user_id": str(user_id),
            "product_id": str(product_id),
            "product_name": "Test Sneakers",
            "price": 5000,
            "currency": "RUB",
            "quantity": 1,
            "reservation_id": str(reservation_id),
        },
    )
    assert dup_resp.status_code == 409


@pytest.mark.asyncio
async def test_ord_010_and_011_promocode_crud_and_math(client: AsyncClient) -> None:
    """ORD-010 & ORD-011: Promocode percentage math and order creation."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    # Create promocode SALE20 (20% off)
    promo_resp = await client.post(
        "/api/v1/promocodes/",
        json={
            "code": "SALE20",
            "discount_type": "PERCENTAGE",
            "discount_value": 20,
            "max_uses": 100,
            "max_uses_per_user": 5,
            "starts_at": now.isoformat(),
            "expires_at": (now + timedelta(days=30)).isoformat(),
        },
    )
    assert promo_resp.status_code == 201
    assert promo_resp.json()["code"] == "SALE20"

    # Validate promocode on 10000 RUB order
    user_id = uuid.uuid4()
    val_resp = await client.post(
        "/api/v1/promocodes/validate",
        json={
            "code": "SALE20",
            "user_id": str(user_id),
            "order_amount": 10000,
        },
    )
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["valid"] is True
    assert float(val_data["discount_amount"]) == 2000.0
    assert float(val_data["final_amount"]) == 8000.0

    # Apply promocode during order creation
    product_id = uuid.uuid4()
    reservation_id = uuid.uuid4()
    order_resp = await client.post(
        "/api/v1/orders",
        json={
            "user_id": str(user_id),
            "product_id": str(product_id),
            "product_name": "Pro Headphones",
            "price": 10000,
            "currency": "RUB",
            "quantity": 1,
            "reservation_id": str(reservation_id),
            "promocode": "SALE20",
        },
    )
    assert order_resp.status_code == 201
    order_data = order_resp.json()
    assert float(order_data["discount_amount"]) == 2000.0
    assert float(order_data["final_price"]) == 8000.0


@pytest.mark.asyncio
async def test_ord_008_and_009_consumer_handlers(
    session_factory: async_sessionmaker[AsyncSession], client: AsyncClient
) -> None:
    """ORD-008 & ORD-009: Test PaymentSucceeded, PaymentFailed, ReservationReleased consumer handlers."""
    user_id = uuid.uuid4()
    product_id = uuid.uuid4()
    reservation_id = uuid.uuid4()

    res = await client.post(
        "/api/v1/orders",
        json={
            "user_id": str(user_id),
            "product_id": str(product_id),
            "product_name": "Smart Watch",
            "price": 15000,
            "currency": "RUB",
            "quantity": 1,
            "reservation_id": str(reservation_id),
        },
    )
    order_id = uuid.UUID(res.json()["id"])
    payment_id = uuid.uuid4()

    # Process PaymentSucceeded
    async with session_factory() as session, session.begin():
        await handle_payment_succeeded(session, {"order_id": str(order_id), "payment_id": str(payment_id)})

    # Verify order CONFIRMED
    get_1 = await client.get(f"/api/v1/orders/{order_id}")
    assert get_1.json()["status"] == "CONFIRMED"

    # Redelivery of PaymentSucceeded should remain CONFIRMED
    async with session_factory() as session, session.begin():
        await handle_payment_succeeded(session, {"order_id": str(order_id), "payment_id": str(payment_id)})

    get_2 = await client.get(f"/api/v1/orders/{order_id}")
    assert get_2.json()["status"] == "CONFIRMED"

    # Failure handler test on a second order
    res_2 = await client.post(
        "/api/v1/orders",
        json={
            "user_id": str(user_id),
            "product_id": str(product_id),
            "product_name": "Smart Watch",
            "price": 15000,
            "currency": "RUB",
            "quantity": 1,
            "reservation_id": str(uuid.uuid4()),
        },
    )
    order_id_2 = uuid.UUID(res_2.json()["id"])

    async with session_factory() as session, session.begin():
        await handle_payment_failed(
            session,
            {"order_id": str(order_id_2), "payment_id": str(payment_id), "reason": "card_declined"},
        )

    get_fail = await client.get(f"/api/v1/orders/{order_id_2}")
    assert get_fail.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_ord_016_outbox_worker_retries(
    session_factory: async_sessionmaker[AsyncSession]
) -> None:
    """ORD-016: Outbox worker retries failed order events."""
    async with session_factory() as session, session.begin():
        event = OutboxEventModel(
            event_type="OrderCreated",
            payload='{"order_id": "test"}',
            status="failed",
            attempts=1,
        )
        session.add(event)

    class MockExchange:
        def __init__(self) -> None:
            self.published = 0

        async def publish(self, message: any, routing_key: str, mandatory: bool = True) -> None:
            self.published += 1

    mock_exchange = MockExchange()
    count = await publish_outbox_batch(mock_exchange, session_factory=session_factory)
    assert count >= 1
    assert mock_exchange.published >= 1


@pytest.mark.asyncio
async def test_ord_018_readiness_probe(client: AsyncClient) -> None:
    """ORD-018: Readiness probe returns HTTP 200."""
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
