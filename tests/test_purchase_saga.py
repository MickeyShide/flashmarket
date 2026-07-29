"""End-to-end purchase saga integration test.

The test exercises the happy path of a flash-sale purchase:

1. Create a product and category in the catalog.
2. Initialize stock in inventory.
3. Reserve stock for the order.
4. Create an order (orders service emits OrderCreated + PaymentRequested).
5. Confirm the payment (payments service emits PaymentSucceeded).
6. Orders consumer updates the order to CONFIRMED and emits OrderConfirmed.
7. Notifications consumer creates a notification for the user.

The test is designed to run against the full Docker Compose stack. It is
marked with ``integration`` so it can be excluded from fast unit-test runs.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from urllib.parse import urljoin

import aio_pika
import httpx
import pytest

from tests.conftest import RABBITMQ_URL


pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def _poll_until(
    predicate: Callable[[], Awaitable[bool]],
    *,
    timeout: float = 30.0,
    interval: float = 0.5,
) -> None:
    """Wait until predicate returns a truthy value."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if await predicate():
            return
        await asyncio.sleep(interval)
    pytest.fail("Polling condition was not met in time")


async def test_purchase_saga_happy_path(
    api_client: httpx.AsyncClient,
    unique_user: uuid.UUID,
) -> None:
    """Complete a purchase from catalog product to notification."""
    user_id = unique_user

    # 1. Create category and product in catalog.
    category_slug = f"test-category-{uuid.uuid4().hex[:8]}"
    category_resp = await api_client.post(
        "/api/v1/categories",
        json={"name": "Test Category", "slug": category_slug},
    )
    assert category_resp.status_code == 201, category_resp.text
    category_id = category_resp.json()["id"]

    product_name = f"Flash Sneakers {uuid.uuid4().hex[:8]}"
    product_resp = await api_client.post(
        "/api/v1/products",
        json={
            "name": product_name,
            "description": "Limited edition sneakers",
            "price": "9999.00",
            "currency": "RUB",
            "category_id": str(category_id),
            "status": "ACTIVE",
        },
    )
    assert product_resp.status_code == 201, product_resp.text
    product_data = product_resp.json()
    product_id = product_data["id"]

    # 2. Initialize stock.
    stock_resp = await api_client.post(
        "/api/v1/stocks",
        json={"product_id": product_id, "total": 10},
    )
    assert stock_resp.status_code == 201, stock_resp.text

    # 3. Reserve stock.
    reserve_resp = await api_client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={"user_id": str(user_id), "quantity": 1},
    )
    assert reserve_resp.status_code == 201, reserve_resp.text
    reservation_id = reserve_resp.json()["reservation"]["id"]

    # 4. Create order.
    order_resp = await api_client.post(
        "/api/v1/orders",
        json={
            "user_id": str(user_id),
            "product_id": product_id,
            "product_name": product_name,
            "price": 9999,
            "currency": "RUB",
            "quantity": 1,
            "reservation_id": reservation_id,
        },
    )
    assert order_resp.status_code == 201, order_resp.text
    order_data = order_resp.json()
    order_id = order_data["id"]
    assert order_data["status"] == "AWAITING_PAYMENT"

    # 5. Payment service should have created a pending payment.
    payments_resp = await api_client.get(
        f"/api/v1/payments/users/{user_id}",
        params={"limit": 10},
    )
    assert payments_resp.status_code == 200, payments_resp.text
    payment_items = payments_resp.json()["items"]
    assert len(payment_items) == 1, payment_items
    payment_id = payment_items[0]["id"]

    # 6. Confirm payment; this triggers PaymentSucceeded event.
    confirm_resp = await api_client.post(f"/api/v1/payments/{payment_id}/confirm")
    assert confirm_resp.status_code == 200, confirm_resp.text

    # 7. Wait for order to become CONFIRMED.
    async def _order_confirmed() -> bool:
        resp = await api_client.get(f"/api/v1/orders/{order_id}")
        if resp.status_code != 200:
            return False
        return resp.json()["status"] == "CONFIRMED"

    await _poll_until(_order_confirmed, timeout=30.0)

    # 8. Wait for notification to be created.
    async def _notification_created() -> bool:
        resp = await api_client.get(
            f"/api/v1/notifications/users/{user_id}",
            params={"limit": 10},
        )
        if resp.status_code != 200:
            return False
        return len(resp.json()["items"]) > 0

    await _poll_until(_notification_created, timeout=30.0)

    notifications_resp = await api_client.get(
        f"/api/v1/notifications/users/{user_id}",
        params={"limit": 10},
    )
    assert notifications_resp.status_code == 200
    notifications = notifications_resp.json()["items"]
    assert any(n["subject"] == "Order confirmed" for n in notifications)


async def test_purchase_saga_payment_failure_cancels_order(
    api_client: httpx.AsyncClient,
    unique_user: uuid.UUID,
) -> None:
    """Failed payment cancels the order and releases stock."""
    user_id = unique_user

    category_slug = f"test-category-{uuid.uuid4().hex[:8]}"
    category_resp = await api_client.post(
        "/api/v1/categories",
        json={"name": "Test Category", "slug": category_slug},
    )
    assert category_resp.status_code == 201
    category_id = category_resp.json()["id"]

    product_name = f"Flash Sneakers {uuid.uuid4().hex[:8]}"
    product_resp = await api_client.post(
        "/api/v1/products",
        json={
            "name": product_name,
            "description": "Limited edition sneakers",
            "price": "9999.00",
            "currency": "RUB",
            "category_id": str(category_id),
            "status": "ACTIVE",
        },
    )
    assert product_resp.status_code == 201
    product_id = product_resp.json()["id"]

    await api_client.post(
        "/api/v1/stocks",
        json={"product_id": product_id, "total": 10},
    )

    reserve_resp = await api_client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={"user_id": str(user_id), "quantity": 1},
    )
    assert reserve_resp.status_code == 201
    reservation_id = reserve_resp.json()["reservation"]["id"]

    order_resp = await api_client.post(
        "/api/v1/orders",
        json={
            "user_id": str(user_id),
            "product_id": product_id,
            "product_name": product_name,
            "price": 9999,
            "currency": "RUB",
            "quantity": 1,
            "reservation_id": reservation_id,
        },
    )
    assert order_resp.status_code == 201
    order_id = order_resp.json()["id"]

    payments_resp = await api_client.get(
        f"/api/v1/payments/users/{user_id}",
        params={"limit": 10},
    )
    payment_id = payments_resp.json()["items"][0]["id"]

    # Fail payment.
    fail_resp = await api_client.post(f"/api/v1/payments/{payment_id}/fail")
    assert fail_resp.status_code == 200

    async def _order_cancelled() -> bool:
        resp = await api_client.get(f"/api/v1/orders/{order_id}")
        if resp.status_code != 200:
            return False
        return resp.json()["status"] == "CANCELLED"

    await _poll_until(_order_cancelled, timeout=30.0)

    async def _cancellation_notification_created() -> bool:
        resp = await api_client.get(
            f"/api/v1/notifications/users/{user_id}",
            params={"limit": 10},
        )
        if resp.status_code != 200:
            return False
        return any(n["subject"] == "Order cancelled" for n in resp.json()["items"])

    await _poll_until(_cancellation_notification_created, timeout=30.0)
