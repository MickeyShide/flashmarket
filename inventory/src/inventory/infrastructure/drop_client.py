"""Small HTTP client for authoritative public Drop purchase rules."""

from dataclasses import dataclass
from uuid import UUID

import httpx

from inventory.domain.exceptions import DropPurchaseDenied, DropServiceUnavailable


@dataclass(frozen=True, slots=True)
class DropPolicy:
    id: UUID
    status: str
    product_ids: frozenset[UUID]
    max_per_user: int
    payment_timeout_seconds: int


class DropClient:
    def __init__(self, base_url: str, timeout_seconds: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def get_policy(self, drop_id: UUID) -> DropPolicy:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/api/v1/drops/id/{drop_id}")
        except httpx.HTTPError as exc:
            raise DropServiceUnavailable() from exc
        if response.status_code == 404:
            raise DropPurchaseDenied("Drop is not available")
        if not response.is_success:
            raise DropServiceUnavailable()
        try:
            data = response.json()
            return DropPolicy(
                id=UUID(str(data["id"])),
                status=str(data["status"]),
                product_ids=frozenset(UUID(str(item["product_id"])) for item in data["items"]),
                max_per_user=int(data["max_per_user"]),
                payment_timeout_seconds=int(data["payment_timeout_seconds"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise DropServiceUnavailable("Invalid Drop policy response") from exc
