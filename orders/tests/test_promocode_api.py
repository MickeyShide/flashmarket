"""Integration tests for Promocodes API endpoints and order creation with promocodes."""

import uuid
from datetime import UTC, datetime, timedelta
from httpx import AsyncClient

import pytest


@pytest.mark.asyncio
async def test_create_promocode_201(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    payload = {
        "code": "PROMO2026",
        "discount_type": "FIXED",
        "discount_value": 300,
        "currency": "RUB",
        "starts_at": (now - timedelta(hours=1)).isoformat(),
        "expires_at": (now + timedelta(days=7)).isoformat(),
    }

    response = await client.post("/api/v1/promocodes/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["code"] == "PROMO2026"
    assert data["discount_type"] == "FIXED"
    assert float(data["discount_value"]) == 300.0
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_create_duplicate_promocode_409(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    payload = {
        "code": "DUPPROMO",
        "discount_type": "FIXED",
        "discount_value": 100,
        "starts_at": (now - timedelta(hours=1)).isoformat(),
        "expires_at": (now + timedelta(days=7)).isoformat(),
    }

    await client.post("/api/v1/promocodes/", json=payload)
    response = await client.post("/api/v1/promocodes/", json=payload)

    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "duplicate_promocode_code"


@pytest.mark.asyncio
async def test_validate_promocode_endpoint(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    await client.post(
        "/api/v1/promocodes/",
        json={
            "code": "VALID10",
            "discount_type": "PERCENTAGE",
            "discount_value": 10,
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
        },
    )

    user_id = uuid.uuid4()
    response = await client.post(
        "/api/v1/promocodes/validate",
        json={
            "code": "valid10",
            "user_id": str(user_id),
            "order_amount": 1000,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert float(data["discount_amount"]) == 100.0
    assert float(data["final_amount"]) == 900.0
    assert data["error"] is None


@pytest.mark.asyncio
async def test_order_creation_with_promocode(client: AsyncClient) -> None:
    now = datetime.now(UTC)
    await client.post(
        "/api/v1/promocodes/",
        json={
            "code": "ORDERPROMO",
            "discount_type": "FIXED",
            "discount_value": 200,
            "starts_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
        },
    )

    user_id = uuid.uuid4()
    prod_id = uuid.uuid4()
    res_id = uuid.uuid4()

    order_payload = {
        "user_id": str(user_id),
        "product_id": str(prod_id),
        "product_name": "Test Item",
        "price": 1000,
        "quantity": 1,
        "reservation_id": str(res_id),
        "promocode": "ORDERPROMO",
    }

    response = await client.post("/api/v1/orders", json=order_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == str(user_id)
    assert data["promocode_id"] is not None
    assert float(data["discount_amount"]) == 200.0
    assert float(data["final_price"]) == 800.0
