"""Tests for product business logic via the HTTP API."""

import uuid

from httpx import AsyncClient


async def _create_category(
    client: AsyncClient, name: str = "Electronics", slug: str | None = None
) -> str:
    if slug is None:
        slug = f"cat-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/categories",
        json={"name": name, "slug": slug},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_product(
    client: AsyncClient,
    category_id: str,
    name: str = "Laptop",
    price: str = "999.99",
    status: str = "ACTIVE",
) -> dict:
    resp = await client.post(
        "/api/v1/products",
        json={
            "name": name,
            "price": price,
            "category_id": category_id,
            "status": status,
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def test_create_product(client: AsyncClient) -> None:
    """Creating a product returns all expected fields."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id)

    assert product["name"] == "Laptop"
    assert product["slug"] == "laptop"
    assert product["category_id"] == cat_id
    assert product["category_name"] == "Electronics"
    assert product["status"] == "ACTIVE"
    assert product["currency"] == "RUB"
    assert float(product["price"]) == 999.99


async def test_create_product_invalid_category(client: AsyncClient) -> None:
    """Non-existent category should return 404."""
    resp = await client.post(
        "/api/v1/products",
        json={
            "name": "Ghost",
            "price": "10.00",
            "category_id": "00000000-0000-0000-0000-000000000001",
        },
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "category_not_found"


async def test_create_product_sets_published_at(client: AsyncClient) -> None:
    """ACTIVE product should have published_at set."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id, status="ACTIVE")
    assert product["published_at"] is not None


async def test_create_product_hidden_no_published(client: AsyncClient) -> None:
    """HIDDEN product should have published_at=null."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id, status="HIDDEN")
    assert product["published_at"] is None


async def test_get_product_active(client: AsyncClient) -> None:
    """ACTIVE products are visible via public slug endpoint."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id, name="Visible")

    resp = await client.get(f"/api/v1/products/{product['slug']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Visible"


async def test_get_product_hidden_404(client: AsyncClient) -> None:
    """HIDDEN products return 404 on the public endpoint."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id, name="Secret", status="HIDDEN")

    resp = await client.get(f"/api/v1/products/{product['slug']}")
    assert resp.status_code == 404


async def test_get_product_archived_404(client: AsyncClient) -> None:
    """ARCHIVED products return 404 on the public endpoint."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id, name="Old")

    # Archive it
    resp = await client.delete(f"/api/v1/products/{product['id']}")
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/products/{product['slug']}")
    assert resp.status_code == 404


async def test_archive_product(client: AsyncClient) -> None:
    """Archiving sets status to ARCHIVED."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id)

    resp = await client.delete(f"/api/v1/products/{product['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ARCHIVED"


async def test_archive_nonexistent(client: AsyncClient) -> None:
    """Archiving a non-existent product returns 404."""
    resp = await client.delete("/api/v1/products/00000000-0000-0000-0000-000000000001")
    assert resp.status_code == 404


async def test_update_product_partial(client: AsyncClient) -> None:
    """PATCH only the name; slug must NOT change."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id, name="Original")
    original_slug = product["slug"]

    resp = await client.patch(
        f"/api/v1/products/{product['id']}",
        json={"name": "Updated Name"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Name"
    assert data["slug"] == original_slug


async def test_update_product_status_sets_published(client: AsyncClient) -> None:
    """Changing status from HIDDEN to ACTIVE sets published_at."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id, status="HIDDEN")
    assert product["published_at"] is None

    resp = await client.patch(
        f"/api/v1/products/{product['id']}",
        json={"status": "ACTIVE"},
    )
    assert resp.status_code == 200
    assert resp.json()["published_at"] is not None


async def test_price_must_be_positive(client: AsyncClient) -> None:
    """Price <= 0 should be rejected by Pydantic validation."""
    cat_id = await _create_category(client)
    resp = await client.post(
        "/api/v1/products",
        json={
            "name": "Free Stuff",
            "price": "0",
            "category_id": cat_id,
        },
    )
    assert resp.status_code == 422
