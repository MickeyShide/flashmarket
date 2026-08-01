"""PostgreSQL-backed concurrency test for the reservation path.

This test requires a running PostgreSQL instance reachable via
INVENTORY_DATABASE_URL. It is skipped automatically when Postgres is
unavailable so that the fast SQLite unit-test suite still runs by default.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from inventory.application.contracts import NoOpStockCache
from inventory.application.schemas import ReserveRequest
from inventory.application.services.stock import InventoryService
from inventory.infrastructure.database import Base
from inventory.infrastructure.models import StockModel
from inventory.infrastructure.repositories.stock import (
    OutboxRepository,
    ReservationRepository,
    StockRepository,
)


@pytest.fixture(scope="module")
def postgres_url() -> str | None:
    url = os.environ.get(
        "INVENTORY_DATABASE_URL",
        "postgresql+asyncpg://flashmarket:flashmarket@localhost:5434/inventory",
    )
    return url if url.startswith("postgresql+asyncpg://") else None


@pytest_asyncio.fixture(loop_scope="module", scope="module")
async def session_factory(
    postgres_url: str | None,
) -> AsyncIterator[async_sessionmaker[AsyncSession] | None]:
    if postgres_url is None:
        yield None
        return

    engine = create_async_engine(postgres_url, pool_size=50, max_overflow=100)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.skipif(
    os.environ.get("INVENTORY_DATABASE_URL", "").startswith("sqlite")
    or "INVENTORY_DATABASE_URL" not in os.environ,
    reason="Requires a real PostgreSQL database",
)
@pytest.mark.asyncio(loop_scope="module")
async def test_concurrent_reservations_no_oversell(
    session_factory: async_sessionmaker[AsyncSession] | None,
) -> None:
    """2000 concurrent buyers cannot reserve more than 100 units."""
    assert session_factory is not None

    product_id = uuid.uuid7()
    async with session_factory() as db:
        service = InventoryService(
            session=db,
            stock_repo=StockRepository(db),
            reservation_repo=ReservationRepository(db),
            outbox_repo=OutboxRepository(db),
            stock_cache=NoOpStockCache(),
        )
        await service.create_stock(
            type("Data", (), {"product_id": product_id, "variant_id": None, "total": 100})()
        )

    semaphore = asyncio.Semaphore(20)

    async def reserve_one() -> int:
        async with semaphore:
            async with session_factory() as db:
                service = InventoryService(
                    session=db,
                    stock_repo=StockRepository(db),
                    reservation_repo=ReservationRepository(db),
                    outbox_repo=OutboxRepository(db),
                    stock_cache=NoOpStockCache(),
                )
                try:
                    await service.reserve(
                        product_id,
                        ReserveRequest(user_id=uuid.uuid7(), quantity=1),
                    )
                except Exception:
                    return 0
                return 1

    results = await asyncio.gather(*[reserve_one() for _ in range(2000)])
    reserved = sum(results)

    assert 0 <= reserved <= 100

    async with session_factory() as db:
        stock = await db.scalar(select(StockModel).where(StockModel.product_id == product_id))
        assert stock is not None
        assert stock.reserved == reserved
        assert stock.available == 100 - reserved
        assert stock.reserved + stock.sold <= stock.total
