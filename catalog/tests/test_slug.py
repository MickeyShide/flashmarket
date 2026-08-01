"""Tests for automatic slug generation and uniqueness."""

import uuid

from httpx import AsyncClient


async def _create_category(client: AsyncClient) -> str:
    """Create a category and return its id."""
    slug = f"cat-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/categories",
        json={"name": "General", "slug": slug},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


async def test_slug_basic_generation(client: AsyncClient) -> None:
    """A simple name should be slugified correctly."""
    category_id = await _create_category(client)
    resp = await client.post(
        "/api/v1/products",
        json={
            "name": "iPhone 17 Pro",
            "price": "129990.00",
            "category_id": category_id,
        },
    )
    assert resp.status_code == 201
    assert resp.json()["slug"] == "iphone-17-pro"


async def test_slug_special_characters(client: AsyncClient) -> None:
    """Special characters and accents should be stripped or transliterated."""
    category_id = await _create_category(client)
    resp = await client.post(
        "/api/v1/products",
        json={
            "name": "Café & Résumé!",
            "price": "100.00",
            "category_id": category_id,
        },
    )
    assert resp.status_code == 201
    slug = resp.json()["slug"]
    assert slug
    # Should only contain lowercase letters, digits, and hyphens
    assert all(c in "abcdefghijklmnopqrstuvwxyz0123456789-" for c in slug)


async def test_slug_uniqueness_suffix(client: AsyncClient) -> None:
    """Duplicate names should get a numeric suffix."""
    category_id = await _create_category(client)

    resp1 = await client.post(
        "/api/v1/products",
        json={"name": "Test Product", "price": "10.00", "category_id": category_id},
    )
    assert resp1.status_code == 201
    assert resp1.json()["slug"] == "test-product"

    resp2 = await client.post(
        "/api/v1/products",
        json={"name": "Test Product", "price": "20.00", "category_id": category_id},
    )
    assert resp2.status_code == 201
    assert resp2.json()["slug"] == "test-product-2"


async def test_slug_uniqueness_chain(client: AsyncClient) -> None:
    """Three products with the same name get -2 and -3 suffixes."""
    category_id = await _create_category(client)

    slugs = []
    for i in range(3):
        resp = await client.post(
            "/api/v1/products",
            json={
                "name": "Chain Item",
                "price": str(10 + i),
                "category_id": category_id,
            },
        )
        assert resp.status_code == 201
        slugs.append(resp.json()["slug"])

    assert slugs == ["chain-item", "chain-item-2", "chain-item-3"]


async def test_slug_format_validation(client: AsyncClient) -> None:
    """Generated slugs must match [a-z0-9-] pattern."""
    category_id = await _create_category(client)
    resp = await client.post(
        "/api/v1/products",
        json={
            "name": "Hello World 2026!",
            "price": "1.00",
            "category_id": category_id,
        },
    )
    assert resp.status_code == 201
    slug = resp.json()["slug"]
    import re

    assert re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug)
