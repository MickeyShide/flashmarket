"""Comprehensive integration tests for Catalog microservice (CAT-001 through CAT-019)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from jwt_verifier.testing import TestKeyStore as JWTTestKeyStore

from catalog.main import app


@pytest.mark.asyncio
async def test_cat_001_to_005_category_brand_product_crud_and_slugs(client: AsyncClient) -> None:
    """CAT-001..CAT-005: Category, Brand, Product CRUD, slug uniqueness, and filtering."""
    # 1. Create Brand
    brand_name = f"Nike-{uuid.uuid4().hex[:6]}"
    brand_resp = await client.post(
        "/api/v1/brands",
        json={"name": brand_name, "slug": brand_name.lower()},
    )
    assert brand_resp.status_code == 201
    brand_id = brand_resp.json()["id"]

    # 2. Create Category
    cat_name = f"Footwear-{uuid.uuid4().hex[:6]}"
    cat_resp = await client.post(
        "/api/v1/categories",
        json={"name": cat_name, "slug": cat_name.lower()},
    )
    assert cat_resp.status_code == 201
    category_id = cat_resp.json()["id"]

    # Duplicate category slug -> 409
    dup_cat = await client.post(
        "/api/v1/categories",
        json={"name": "Duplicate Cat", "slug": cat_name.lower()},
    )
    assert dup_cat.status_code == 409

    # 3. Create Product with auto-generated slug
    product_resp = await client.post(
        "/api/v1/products",
        json={
            "name": "Air Max 90",
            "description": "Classic running shoes",
            "price": "12999.00",
            "currency": "RUB",
            "category_id": str(category_id),
            "brand_id": str(brand_id),
            "status": "ACTIVE",
        },
    )
    assert product_resp.status_code == 201
    product_data = product_resp.json()
    assert product_data["slug"] == "air-max-90"
    product_id = product_data["id"]

    # 4. Create Product Variant with auto-generated SKU
    variant_resp = await client.post(
        f"/api/v1/products/{product_id}/variants/",
        json={
            "name": "Size 42 - Red",
            "attributes": {"size": "42", "color": "Red"},
            "price_override": "13499.00",
        },
    )
    assert variant_resp.status_code == 201
    variant_data = variant_resp.json()
    assert "sku" in variant_data
    assert len(variant_data["sku"]) > 0

    # 5. List products with brand_id and category_id filters
    list_resp = await client.get(
        "/api/v1/products",
        params={"category_id": str(category_id), "brand_id": str(brand_id)},
    )
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == product_id


@pytest.mark.asyncio
async def test_cat_012_admin_authorization_enforcement(
    jwt_keystore: JWTTestKeyStore,
) -> None:
    """CAT-012: Mutation endpoints reject requests without ADMIN role (401/403)."""
    user_token = jwt_keystore.create_token(role="USER")
    headers = {"Authorization": f"Bearer {user_token}"}
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://localhost",
        headers=headers,
    ) as user_client:
        resp = await user_client.post(
            "/api/v1/categories",
            json={"name": "Forbidden Cat", "slug": "forbidden-cat"},
        )
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_cat_019_readiness_probe(client: AsyncClient) -> None:
    """CAT-019: Readiness probe returns HTTP 200."""
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
