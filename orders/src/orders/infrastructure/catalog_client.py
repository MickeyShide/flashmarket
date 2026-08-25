"""HTTP client for authoritative Catalog pricing."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

import httpx


@dataclass(frozen=True, slots=True)
class CatalogProductPrice:
    product_id: UUID
    price: Decimal
    currency: str
    variant_id: UUID | None = None


class CatalogClient:
    def __init__(self, base_url: str, timeout_seconds: float = 3.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def get_price(
        self, product_id: UUID, variant_id: UUID | None = None
    ) -> CatalogProductPrice | None:
        """Fetch authoritative price for a product from the Catalog service."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/api/v1/products/{product_id}")
                if response.status_code == 200:
                    data = response.json()
                    price = Decimal(str(data["price"]))
                    if variant_id is not None:
                        for v in data.get("variants", []):
                            if str(v.get("id")) == str(variant_id):
                                if v.get("price_override") is not None:
                                    price = Decimal(str(v["price_override"]))
                                elif v.get("effective_price") is not None:
                                    price = Decimal(str(v["effective_price"]))
                                break

                    return CatalogProductPrice(
                        product_id=UUID(str(data["id"])),
                        price=price,
                        currency=str(data.get("currency", "RUB")),
                        variant_id=variant_id,
                    )
        except Exception:
            pass
        return None
