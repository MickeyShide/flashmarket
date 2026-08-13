"""Integration tests for Wishlist API endpoints."""

import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_add_item_201(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    product_id = uuid.uuid4()

    response = await client.post(
        f"/api/v1/wishlist/users/{user_id}/items",
        json={"product_id": str(product_id)},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == str(user_id)
    assert data["product_id"] == str(product_id)
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_add_duplicate_409(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    product_id = uuid.uuid4()

    await client.post(
        f"/api/v1/wishlist/users/{user_id}/items",
        json={"product_id": str(product_id)},
    )

    response = await client.post(
        f"/api/v1/wishlist/users/{user_id}/items",
        json={"product_id": str(product_id)},
    )

    assert response.status_code == 409
    data = response.json()
    assert data["error"]["code"] == "item_already_in_wishlist"


@pytest.mark.asyncio
async def test_remove_item_204(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    product_id = uuid.uuid4()

    await client.post(
        f"/api/v1/wishlist/users/{user_id}/items",
        json={"product_id": str(product_id)},
    )

    response = await client.delete(
        f"/api/v1/wishlist/users/{user_id}/items/{product_id}"
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_remove_nonexistent_404(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    product_id = uuid.uuid4()

    response = await client.delete(
        f"/api/v1/wishlist/users/{user_id}/items/{product_id}"
    )

    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "item_not_in_wishlist"


@pytest.mark.asyncio
async def test_list_items_200(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    prod_a = uuid.uuid4()
    prod_b = uuid.uuid4()

    await client.post(
        f"/api/v1/wishlist/users/{user_id}/items",
        json={"product_id": str(prod_a)},
    )
    await client.post(
        f"/api/v1/wishlist/users/{user_id}/items",
        json={"product_id": str(prod_b)},
    )

    response = await client.get(f"/api/v1/wishlist/users/{user_id}/items?limit=10&offset=0")

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["limit"] == 10
    assert data["offset"] == 0


@pytest.mark.asyncio
async def test_check_items_200(client: AsyncClient) -> None:
    user_id = uuid.uuid4()
    prod_a = uuid.uuid4()
    prod_b = uuid.uuid4()
    prod_c = uuid.uuid4()

    await client.post(
        f"/api/v1/wishlist/users/{user_id}/items",
        json={"product_id": str(prod_a)},
    )

    response = await client.post(
        f"/api/v1/wishlist/users/{user_id}/check",
        json={"product_ids": [str(prod_a), str(prod_b), str(prod_c)]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["product_ids"] == [str(prod_a)]


@pytest.mark.asyncio
async def test_health_ready_200(client: AsyncClient) -> None:
    response = await client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
