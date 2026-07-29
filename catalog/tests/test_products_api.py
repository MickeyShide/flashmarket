"""HTTP-level tests for product listing, filtering, sorting, and pagination."""

from httpx import AsyncClient


async def _create_category(
    client: AsyncClient, name: str = "Default", slug: str = "default"
) -> str:
    resp = await client.post("/api/v1/categories", json={"name": name, "slug": slug})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_product(
    client: AsyncClient,
    category_id: str,
    name: str = "Item",
    price: str = "100.00",
    status: str = "ACTIVE",
    description: str = "",
) -> dict:
    resp = await client.post(
        "/api/v1/products",
        json={
            "name": name,
            "price": price,
            "category_id": category_id,
            "status": status,
            "description": description,
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def test_create_product_201(client: AsyncClient) -> None:
    """POST /api/v1/products returns 201 with correct body."""
    cat_id = await _create_category(client)
    resp = await client.post(
        "/api/v1/products",
        json={
            "name": "Widget",
            "price": "42.50",
            "category_id": cat_id,
            "status": "ACTIVE",
            "cover_image": "https://cdn.example.com/widget.jpg",
            "images": [
                {"url": "https://cdn.example.com/w1.jpg", "sort_order": 0},
                {"url": "https://cdn.example.com/w2.jpg", "sort_order": 1},
            ],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Widget"
    assert len(data["images"]) == 2
    assert data["cover_image"] == "https://cdn.example.com/widget.jpg"


async def test_create_product_invalid_422(client: AsyncClient) -> None:
    """Missing required fields should return 422."""
    resp = await client.post("/api/v1/products", json={})
    assert resp.status_code == 422


async def test_get_product_by_slug_200(client: AsyncClient) -> None:
    """GET /api/v1/products/{slug} for an ACTIVE product returns 200."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id, name="Findable")
    resp = await client.get(f"/api/v1/products/{product['slug']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == product["id"]


async def test_get_product_hidden_404(client: AsyncClient) -> None:
    """GET /api/v1/products/{slug} for a HIDDEN product returns 404."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id, name="Invisible", status="HIDDEN")
    resp = await client.get(f"/api/v1/products/{product['slug']}")
    assert resp.status_code == 404


async def test_list_products_pagination(client: AsyncClient) -> None:
    """Pagination should return the correct slice and total."""
    cat_id = await _create_category(client)
    for i in range(5):
        await _create_product(client, cat_id, name=f"Prod {i}", price=str(10 + i))

    resp = await client.get("/api/v1/products", params={"limit": 2, "offset": 0})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["items"]) == 2
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 0


async def test_list_products_filter_category(client: AsyncClient) -> None:
    """Filtering by category_id should only return matching products."""
    cat_a = await _create_category(client, name="A", slug="a")
    cat_b = await _create_category(client, name="B", slug="b")
    await _create_product(client, cat_a, name="In A")
    await _create_product(client, cat_b, name="In B")

    resp = await client.get("/api/v1/products", params={"category_id": cat_a})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "In A"


async def test_list_products_filter_price_range(client: AsyncClient) -> None:
    """Filtering by price range should narrow results."""
    cat_id = await _create_category(client)
    await _create_product(client, cat_id, name="Cheap", price="50.00")
    await _create_product(client, cat_id, name="Mid", price="200.00")
    await _create_product(client, cat_id, name="Expensive", price="1000.00")

    resp = await client.get("/api/v1/products", params={"price_from": 100, "price_to": 500})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Mid"


async def test_list_products_search(client: AsyncClient) -> None:
    """ILIKE search by name and description."""
    cat_id = await _create_category(client)
    await _create_product(client, cat_id, name="iPhone Case", description="Protective case")
    await _create_product(client, cat_id, name="Samsung Cable", description="USB-C cable")

    resp = await client.get("/api/v1/products", params={"search": "iphone"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "iPhone Case"


async def test_list_products_sort_price_asc(client: AsyncClient) -> None:
    """Sorting by price ascending should order from cheapest."""
    cat_id = await _create_category(client)
    await _create_product(client, cat_id, name="B", price="200.00")
    await _create_product(client, cat_id, name="A", price="50.00")
    await _create_product(client, cat_id, name="C", price="500.00")

    resp = await client.get("/api/v1/products", params={"sort_by": "price", "sort_order": "asc"})
    assert resp.status_code == 200
    prices = [float(item["price"]) for item in resp.json()["items"]]
    assert prices == sorted(prices)


async def test_list_products_sort_name(client: AsyncClient) -> None:
    """Sorting by name should order alphabetically."""
    cat_id = await _create_category(client)
    await _create_product(client, cat_id, name="Zebra")
    await _create_product(client, cat_id, name="Apple")
    await _create_product(client, cat_id, name="Mango")

    resp = await client.get("/api/v1/products", params={"sort_by": "name", "sort_order": "asc"})
    assert resp.status_code == 200
    names = [item["name"] for item in resp.json()["items"]]
    assert names == sorted(names)


async def test_update_product_200(client: AsyncClient) -> None:
    """PATCH /api/v1/products/{id} should update and return the product."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id, name="Old Name")

    resp = await client.patch(
        f"/api/v1/products/{product['id']}",
        json={"name": "New Name", "price": "777.00"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert float(data["price"]) == 777.00


async def test_archive_product_200(client: AsyncClient) -> None:
    """DELETE /api/v1/products/{id} should return ARCHIVED status."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id)

    resp = await client.delete(f"/api/v1/products/{product['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ARCHIVED"


async def test_internal_get_any_status(client: AsyncClient) -> None:
    """Internal endpoint should return HIDDEN products."""
    cat_id = await _create_category(client)
    product = await _create_product(client, cat_id, name="Hidden", status="HIDDEN")

    resp = await client.get(f"/api/v1/internal/products/{product['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "HIDDEN"
