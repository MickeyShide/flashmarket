"""Integration tests for Product Variants API endpoints."""

import uuid

import pytest
from httpx import AsyncClient


async def _setup_category_and_product(client: AsyncClient):
    cat_res = await client.post(
        "/api/v1/categories",
        json={"name": "Shoes", "slug": f"shoes-{uuid.uuid4().hex[:8]}"},
    )
    assert cat_res.status_code == 201
    cat_id = cat_res.json()["id"]

    prod_res = await client.post(
        "/api/v1/products",
        json={
            "name": "Sneakers",
            "price": 10000,
            "category_id": cat_id,
        },
    )
    assert prod_res.status_code == 201
    return prod_res.json()["id"]


@pytest.mark.asyncio
async def test_variants_crud_flow(client: AsyncClient) -> None:
    product_id = await _setup_category_and_product(client)

    # 1. Create variant
    create_res = await client.post(
        f"/api/v1/products/{product_id}/variants/",
        json={
            "size": "42",
            "color": "White",
            "color_hex": "#FFFFFF",
            "price_override": 11000,
        },
    )
    assert create_res.status_code == 201
    v_data = create_res.json()
    variant_id = v_data["id"]
    assert v_data["size"] == "42"
    assert v_data["sku"] == "SNE-WHI-42"
    assert float(v_data["effective_price"]) == 11000.0

    # 2. Get list of variants
    list_res = await client.get(f"/api/v1/products/{product_id}/variants/")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    # 3. Get single variant
    get_res = await client.get(f"/api/v1/products/{product_id}/variants/{variant_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == variant_id

    # 4. Patch variant
    patch_res = await client.patch(
        f"/api/v1/products/{product_id}/variants/{variant_id}",
        json={"color": "Off-White"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["color"] == "Off-White"

    # 5. Verify product endpoint includes variants
    prod_get = await client.get(f"/api/v1/products/{product_id}")
    assert prod_get.status_code == 200
    prod_data = prod_get.json()
    assert "variants" in prod_data
    assert len(prod_data["variants"]) == 1
    assert prod_data["variants"][0]["id"] == variant_id

    # 6. Delete variant
    del_res = await client.delete(f"/api/v1/products/{product_id}/variants/{variant_id}")
    assert del_res.status_code == 204

    # 7. Check list empty
    list_after = await client.get(f"/api/v1/products/{product_id}/variants/")
    assert list_after.status_code == 200
    assert len(list_after.json()) == 0
