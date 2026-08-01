"""Tests for the revision-aware Inventory stock cache."""

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from aio_pika.abc import AbstractIncomingMessage
from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from inventory.application.contracts import StockCacheStoreResult
from inventory.application.schemas import (
    CommitRequest,
    ReleaseRequest,
    ReserveRequest,
    StockCreateRequest,
    StockResponse,
    StockUpdateRequest,
)
from inventory.application.services.stock import InventoryService
from inventory.config import Settings
from inventory.domain.exceptions import StockNotFound
from inventory.event_consumer import process_message
from inventory.infrastructure.models import StockModel
from inventory.infrastructure.repositories.stock import (
    OutboxRepository,
    ReservationRepository,
    StockRepository,
)
from inventory.infrastructure.stock_cache import RedisStockCache, stock_cache_key


class _VersionedRedis:
    """Small Redis test double implementing the cache's command subset."""

    def __init__(self) -> None:
        self.values: dict[str, dict[str, str]] = {}
        self.ttls: dict[str, int] = {}

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.values.get(key, {}))

    async def eval(
        self,
        _script: str,
        _numkeys: int,
        key: str,
        revision: int,
        payload: str,
        ttl: int,
    ) -> int:
        current = self.values.get(key, {}).get("revision")
        if current is not None and int(current) > int(revision):
            return 0
        self.values[key] = {"revision": str(revision), "payload": payload}
        self.ttls[key] = ttl
        return 1

    async def delete(self, key: str) -> int:
        existed = key in self.values
        self.values.pop(key, None)
        self.ttls.pop(key, None)
        return int(existed)


class _FailingRedis:
    async def hgetall(self, _key: str) -> dict[str, str]:
        raise RedisError("unavailable")

    async def eval(self, *_args: object) -> int:
        raise RedisError("unavailable")

    async def delete(self, _key: str) -> int:
        raise RedisError("unavailable")


class _RecordingCache:
    def __init__(self) -> None:
        self.snapshots: list[tuple[StockResponse, int]] = []

    async def get_stock(
        self,
        product_id: uuid.UUID,
        variant_id: uuid.UUID | None,
    ) -> StockResponse | None:
        del product_id, variant_id
        return None

    async def store_stock(
        self,
        stock: StockResponse,
        revision: int,
    ) -> StockCacheStoreResult:
        self.snapshots.append((stock, revision))
        return StockCacheStoreResult.STORED


def _snapshot(
    *,
    product_id: uuid.UUID | None = None,
    variant_id: uuid.UUID | None = None,
    available: int = 10,
) -> StockResponse:
    now = datetime.now(UTC)
    return StockResponse(
        id=uuid.uuid7(),
        product_id=product_id or uuid.uuid7(),
        variant_id=variant_id,
        total=10,
        available=available,
        reserved=10 - available,
        sold=0,
        created_at=now,
        updated_at=now,
    )


async def test_cache_round_trip_ttl_and_key_isolation() -> None:
    client = _VersionedRedis()
    cache = RedisStockCache(cast(Redis, client), ttl_seconds=30)
    product_id = uuid.uuid7()
    variant_id = uuid.uuid7()
    base = _snapshot(product_id=product_id)
    variant = _snapshot(product_id=product_id, variant_id=variant_id, available=4)

    assert await cache.store_stock(base, revision=1) == StockCacheStoreResult.STORED
    assert await cache.store_stock(variant, revision=2) == StockCacheStoreResult.STORED

    assert await cache.get_stock(product_id, None) == base
    assert await cache.get_stock(product_id, variant_id) == variant
    assert stock_cache_key(product_id, None) != stock_cache_key(product_id, variant_id)
    assert client.ttls[stock_cache_key(product_id, None)] == 30


async def test_lower_revision_cannot_replace_newer_snapshot() -> None:
    client = _VersionedRedis()
    cache = RedisStockCache(cast(Redis, client), ttl_seconds=30)
    product_id = uuid.uuid7()
    current = _snapshot(product_id=product_id, available=3)
    stale = current.model_copy(update={"available": 8, "reserved": 2})

    assert await cache.store_stock(current, revision=4) == StockCacheStoreResult.STORED
    assert await cache.store_stock(stale, revision=3) == StockCacheStoreResult.STALE
    assert await cache.get_stock(product_id, None) == current


async def test_equal_revision_can_repair_snapshot() -> None:
    client = _VersionedRedis()
    cache = RedisStockCache(cast(Redis, client), ttl_seconds=30)
    stock = _snapshot()

    assert await cache.store_stock(stock, revision=2) == StockCacheStoreResult.STORED
    assert await cache.store_stock(stock, revision=2) == StockCacheStoreResult.STORED


async def test_malformed_or_mismatched_value_is_deleted() -> None:
    client = _VersionedRedis()
    cache = RedisStockCache(cast(Redis, client), ttl_seconds=30)
    product_id = uuid.uuid7()
    key = stock_cache_key(product_id, None)
    client.values[key] = {"revision": "1", "payload": "not-json"}

    assert await cache.get_stock(product_id, None) is None
    assert key not in client.values

    other_stock = _snapshot()
    client.values[key] = {"revision": "1", "payload": other_stock.model_dump_json()}
    assert await cache.get_stock(product_id, None) is None
    assert key not in client.values


async def test_redis_failures_are_fail_open() -> None:
    cache = RedisStockCache(cast(Redis, _FailingRedis()), ttl_seconds=30)
    stock = _snapshot()

    assert await cache.get_stock(stock.product_id, stock.variant_id) is None
    assert await cache.store_stock(stock, revision=1) == StockCacheStoreResult.ERROR


def _service(session: AsyncMock, repository: AsyncMock, cache: AsyncMock) -> InventoryService:
    return InventoryService(
        session=session,
        stock_repo=repository,
        reservation_repo=AsyncMock(),
        outbox_repo=AsyncMock(),
        stock_cache=cache,
    )


async def test_service_cache_hit_skips_repository() -> None:
    session = AsyncMock()
    repository = AsyncMock()
    cache = AsyncMock()
    stock = _snapshot()
    cache.get_stock.return_value = stock

    result = await _service(session, repository, cache).get_stock(stock.product_id)

    assert result == stock
    repository.get_by_product_and_variant.assert_not_awaited()


async def test_service_cache_miss_reads_and_populates() -> None:
    session = AsyncMock()
    repository = AsyncMock()
    cache = AsyncMock()
    cache.get_stock.return_value = None
    stock = StockModel(
        id=uuid.uuid7(),
        product_id=uuid.uuid7(),
        total=10,
        available=10,
        reserved=0,
        sold=0,
        revision=3,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repository.get_by_product_and_variant.return_value = stock

    result = await _service(session, repository, cache).get_stock(stock.product_id)

    assert result.available == 10
    cache.store_stock.assert_awaited_once_with(result, 3)


async def test_service_does_not_negative_cache_missing_stock() -> None:
    session = AsyncMock()
    repository = AsyncMock()
    cache = AsyncMock()
    cache.get_stock.return_value = None
    repository.get_by_product_and_variant.return_value = None

    with pytest.raises(StockNotFound):
        await _service(session, repository, cache).get_stock(uuid.uuid7())

    cache.store_stock.assert_not_awaited()


async def test_mutation_caches_only_after_successful_commit() -> None:
    events: list[str] = []
    session = AsyncMock()
    session.commit.side_effect = lambda: events.append("commit")
    repository = AsyncMock()
    cache = AsyncMock()
    cache.store_stock.side_effect = lambda *_args: events.append("cache")
    stock = StockModel(
        id=uuid.uuid7(),
        product_id=uuid.uuid7(),
        total=10,
        available=10,
        reserved=0,
        sold=0,
        revision=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repository.get_by_product_and_variant_for_update.return_value = stock

    await _service(session, repository, cache).update_total(
        stock.product_id,
        StockUpdateRequest(total=12),
    )

    assert events == ["commit", "cache"]
    assert stock.revision == 2


async def test_failed_commit_does_not_publish_cache_snapshot() -> None:
    session = AsyncMock()
    session.commit.side_effect = RuntimeError("database unavailable")
    repository = AsyncMock()
    cache = AsyncMock()
    stock = StockModel(
        id=uuid.uuid7(),
        product_id=uuid.uuid7(),
        total=10,
        available=10,
        reserved=0,
        sold=0,
        revision=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repository.get_by_product_and_variant_for_update.return_value = stock

    with pytest.raises(RuntimeError, match="database unavailable"):
        await _service(session, repository, cache).update_total(
            stock.product_id,
            StockUpdateRequest(total=12),
        )

    cache.store_stock.assert_not_awaited()


async def test_all_service_mutations_publish_monotonic_revisions(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    cache = _RecordingCache()
    product_id = uuid.uuid7()
    user_id = uuid.uuid7()
    first_order_id = uuid.uuid7()
    second_order_id = uuid.uuid7()

    async with session_factory() as session:
        service = InventoryService(
            session=session,
            stock_repo=StockRepository(session),
            reservation_repo=ReservationRepository(session),
            outbox_repo=OutboxRepository(session),
            stock_cache=cache,
        )
        await service.create_stock(StockCreateRequest(product_id=product_id, total=10))
        await service.reserve(
            product_id,
            ReserveRequest(user_id=user_id, quantity=2, order_id=first_order_id),
        )
        await service.commit(product_id, CommitRequest(order_id=first_order_id))
        await service.reserve(
            product_id,
            ReserveRequest(user_id=user_id, quantity=1, order_id=second_order_id),
        )
        await service.release(product_id, ReleaseRequest(order_id=second_order_id))
        await service.update_total(product_id, StockUpdateRequest(total=12))
        await service.create_stock(StockCreateRequest(product_id=product_id, total=14))

    assert [revision for _, revision in cache.snapshots] == list(range(1, 8))
    assert cache.snapshots[-1][0].available == 12


async def test_expiration_writes_one_final_snapshot_per_stock(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    cache = _RecordingCache()
    product_id = uuid.uuid7()
    user_id = uuid.uuid7()

    async with session_factory() as session:
        service = InventoryService(
            session=session,
            stock_repo=StockRepository(session),
            reservation_repo=ReservationRepository(session),
            outbox_repo=OutboxRepository(session),
            stock_cache=cache,
        )
        await service.create_stock(StockCreateRequest(product_id=product_id, total=5))
        first = await service.reserve(product_id, ReserveRequest(user_id=user_id, quantity=1))
        second = await service.reserve(product_id, ReserveRequest(user_id=user_id, quantity=1))
        first.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        second.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await session.commit()
        cache.snapshots.clear()

        assert await service.expire_reservations() == 2

    assert len(cache.snapshots) == 1
    snapshot, revision = cache.snapshots[0]
    assert revision == 5
    assert snapshot.available == 5
    assert snapshot.reserved == 0


class _IncomingMessage:
    def __init__(self, routing_key: str, payload: str) -> None:
        self.routing_key = routing_key
        self.body = payload.encode()

    @asynccontextmanager
    async def process(self, **_kwargs: Any) -> Any:
        yield self


async def test_consumer_populates_cache_after_transaction_commit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    cache = _RecordingCache()
    product_id = uuid.uuid7()
    order_id = uuid.uuid7()

    async with session_factory() as session:
        service = InventoryService(
            session=session,
            stock_repo=StockRepository(session),
            reservation_repo=ReservationRepository(session),
            outbox_repo=OutboxRepository(session),
            stock_cache=cache,
        )
        await service.create_stock(StockCreateRequest(product_id=product_id, total=3))
        await service.reserve(
            product_id,
            ReserveRequest(user_id=uuid.uuid7(), quantity=1, order_id=order_id),
        )
    cache.snapshots.clear()

    message = _IncomingMessage(
        "payments.PaymentSucceeded",
        f'{{"order_id":"{order_id}"}}',
    )
    await process_message(
        cast(AbstractIncomingMessage, message),
        session_factory=session_factory,
        cache=cache,
    )

    assert len(cache.snapshots) == 1
    snapshot, revision = cache.snapshots[0]
    assert revision == 3
    assert snapshot.available == 2
    assert snapshot.reserved == 0
    assert snapshot.sold == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("stock_cache_ttl_seconds", 0),
        ("redis_socket_timeout_seconds", 0),
    ],
)
def test_cache_settings_must_be_positive(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: value})
