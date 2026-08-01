"""Application-facing contracts for optional infrastructure."""

from enum import StrEnum
from typing import Protocol
from uuid import UUID

from inventory.application.schemas import StockResponse


class StockCacheStoreResult(StrEnum):
    """Outcome of a best-effort stock cache write."""

    STORED = "stored"
    STALE = "stale"
    ERROR = "error"
    SKIPPED = "skipped"


class StockCache(Protocol):
    """Cache operations used by the Inventory application service."""

    async def get_stock(
        self,
        product_id: UUID,
        variant_id: UUID | None,
    ) -> StockResponse | None:
        """Return a cached stock snapshot when one is available."""
        ...

    async def store_stock(
        self,
        stock: StockResponse,
        revision: int,
    ) -> StockCacheStoreResult:
        """Store a snapshot unless a newer revision already exists."""
        ...


class NoOpStockCache:
    """Explicit cache substitute for isolated tests and tooling."""

    async def get_stock(
        self,
        product_id: UUID,
        variant_id: UUID | None,
    ) -> StockResponse | None:
        del product_id, variant_id
        return None

    async def store_stock(
        self,
        stock: StockResponse,
        revision: int,
    ) -> StockCacheStoreResult:
        del stock, revision
        return StockCacheStoreResult.SKIPPED
