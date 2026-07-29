"""Tests for category business logic via the HTTP API."""

from httpx import AsyncClient


async def test_create_category(client: AsyncClient) -> None:
    """Creating a category returns all expected fields."""
    resp = await client.post(
        "/api/v1/categories",
        json={"name": "Furniture", "slug": "furniture"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Furniture"
    assert data["slug"] == "furniture"
    assert data["parent_id"] is None
    assert data["created_at"] is not None


async def test_create_category_duplicate_slug(client: AsyncClient) -> None:
    """Duplicate category slug should return 409."""
    await client.post(
        "/api/v1/categories",
        json={"name": "Tech", "slug": "tech"},
    )
    resp = await client.post(
        "/api/v1/categories",
        json={"name": "Technology", "slug": "tech"},
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "duplicate_slug"


async def test_create_subcategory(client: AsyncClient) -> None:
    """A subcategory should reference its parent."""
    parent_resp = await client.post(
        "/api/v1/categories",
        json={"name": "Electronics", "slug": "electronics"},
    )
    parent_id = parent_resp.json()["id"]

    child_resp = await client.post(
        "/api/v1/categories",
        json={"name": "Phones", "slug": "phones", "parent_id": parent_id},
    )
    assert child_resp.status_code == 201
    assert child_resp.json()["parent_id"] == parent_id


async def test_create_subcategory_invalid_parent(client: AsyncClient) -> None:
    """Non-existent parent_id should return 404."""
    resp = await client.post(
        "/api/v1/categories",
        json={
            "name": "Orphan",
            "slug": "orphan",
            "parent_id": "00000000-0000-0000-0000-000000000001",
        },
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "category_not_found"


async def test_category_tree(client: AsyncClient) -> None:
    """The tree endpoint should return a nested structure."""
    # Create root categories
    elec_resp = await client.post(
        "/api/v1/categories",
        json={"name": "Electronics", "slug": "electronics"},
    )
    elec_id = elec_resp.json()["id"]

    await client.post(
        "/api/v1/categories",
        json={"name": "Furniture", "slug": "furniture"},
    )

    # Create sub-categories under Electronics
    await client.post(
        "/api/v1/categories",
        json={"name": "Phones", "slug": "phones", "parent_id": elec_id},
    )
    await client.post(
        "/api/v1/categories",
        json={"name": "Tablets", "slug": "tablets", "parent_id": elec_id},
    )

    # Fetch tree
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    tree = resp.json()

    # Should have 2 root categories (sorted alphabetically)
    assert len(tree) == 2
    root_names = [node["name"] for node in tree]
    assert "Electronics" in root_names
    assert "Furniture" in root_names

    # Electronics should have 2 children
    electronics = next(n for n in tree if n["name"] == "Electronics")
    assert len(electronics["children"]) == 2
    child_names = {c["name"] for c in electronics["children"]}
    assert child_names == {"Phones", "Tablets"}

    # Furniture should have no children
    furniture = next(n for n in tree if n["name"] == "Furniture")
    assert len(furniture["children"]) == 0
