"""Unit and integration tests for variant-specific stock functionality."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stock_with_variant(client: AsyncClient) -> None:
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()

    # 1. Create stock for a specific variant
    res = await client.post(
        "/api/v1/stocks",
        json={
            "product_id": str(product_id),
            "variant_id": str(variant_id),
            "total": 25,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["product_id"] == str(product_id)
    assert data["variant_id"] == str(variant_id)
    assert data["total"] == 25
    assert data["available"] == 25

    # 2. Query stock for variant
    get_res = await client.get(f"/api/v1/stocks/{product_id}?variant_id={variant_id}")
    assert get_res.status_code == 200
    assert get_res.json()["variant_id"] == str(variant_id)


@pytest.mark.asyncio
async def test_reserve_with_variant(client: AsyncClient) -> None:
    product_id = uuid.uuid4()
    variant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Initialize variant stock
    await client.post(
        "/api/v1/stocks",
        json={
            "product_id": str(product_id),
            "variant_id": str(variant_id),
            "total": 10,
        },
    )

    # Reserve 3 units of variant
    reserve_res = await client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={
            "user_id": str(user_id),
            "variant_id": str(variant_id),
            "quantity": 3,
        },
    )
    assert reserve_res.status_code == 201
    res_data = reserve_res.json()
    assert res_data["stock"]["variant_id"] == str(variant_id)
    assert res_data["stock"]["available"] == 7
    assert res_data["stock"]["reserved"] == 3


@pytest.mark.asyncio
async def test_stock_without_variant_backward_compat(client: AsyncClient) -> None:
    product_id = uuid.uuid4()
    user_id = uuid.uuid4()

    # Initialize stock without variant_id
    res = await client.post(
        "/api/v1/stocks",
        json={
            "product_id": str(product_id),
            "total": 50,
        },
    )
    assert res.status_code == 201
    assert res.json()["variant_id"] is None

    # Reserve without variant_id
    reserve_res = await client.post(
        f"/api/v1/stocks/{product_id}/reserve",
        json={
            "user_id": str(user_id),
            "quantity": 5,
        },
    )
    assert reserve_res.status_code == 201
    assert reserve_res.json()["stock"]["available"] == 45
