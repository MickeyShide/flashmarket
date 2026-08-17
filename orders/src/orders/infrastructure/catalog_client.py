"""HTTP client for authoritative Catalog pricing."""

from dataclasses import dataclass
from uuid import UUID

import httpx


@dataclass(frozen=True, slots=True)
class CatalogProductPrice:
    product_id: UUID
    price: int
    currency: str


class CatalogClient:
    def __init__(self, base_url: str, timeout_seconds: float = 3.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def get_price(self, product_id: UUID) -> CatalogProductPrice | None:
        """Fetch authoritative price for a product from the Catalog service."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/api/v1/products/{product_id}")
                if response.status_code == 200:
                    data = response.json()
                    return CatalogProductPrice(
                        product_id=UUID(str(data["id"])),
                        price=int(data["price"]),
                        currency=str(data.get("currency", "RUB")),
                    )
        except Exception:
            pass
        return None
