"""HTTP-level tests for category endpoints."""

from httpx import AsyncClient


async def test_create_category_201(client: AsyncClient) -> None:
    """POST /api/v1/categories returns 201."""
    resp = await client.post(
        "/api/v1/categories",
        json={"name": "Books", "slug": "books"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Books"
    assert data["slug"] == "books"


async def test_get_category_tree_200(client: AsyncClient) -> None:
    """GET /api/v1/categories returns a tree structure."""
    await client.post(
        "/api/v1/categories",
        json={"name": "Root", "slug": "root"},
    )
    resp = await client.get("/api/v1/categories")
    assert resp.status_code == 200
    tree = resp.json()
    assert isinstance(tree, list)
    assert len(tree) >= 1
    assert tree[0]["children"] is not None


async def test_create_duplicate_slug_409(client: AsyncClient) -> None:
    """Duplicate slug should return 409 Conflict."""
    await client.post(
        "/api/v1/categories",
        json={"name": "Dup", "slug": "dup"},
    )
    resp = await client.post(
        "/api/v1/categories",
        json={"name": "Dup Again", "slug": "dup"},
    )
    assert resp.status_code == 409
