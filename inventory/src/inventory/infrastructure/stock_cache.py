"""Revision-aware, fail-open Redis cache for stock snapshots."""

import logging
from uuid import UUID

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from inventory.application.contracts import StockCacheStoreResult
from inventory.application.schemas import StockResponse
from inventory.config import get_settings
from inventory.observability import STOCK_CACHE_OPERATIONS

STOCK_CACHE_KEY_PREFIX = "inventory:stock"

_STORE_IF_CURRENT_SCRIPT = """
local current_revision = redis.call('HGET', KEYS[1], 'revision')
if current_revision and tonumber(current_revision) > tonumber(ARGV[1]) then
    return 0
end
redis.call('HSET', KEYS[1], 'revision', ARGV[1], 'payload', ARGV[2])
redis.call('EXPIRE', KEYS[1], ARGV[3])
return 1
"""

_logger = logging.getLogger("inventory.stock_cache")


def stock_cache_key(product_id: UUID, variant_id: UUID | None) -> str:
    """Return the isolated Redis key for one product/variant stock row."""
    variant_part = str(variant_id) if variant_id is not None else "default"
    return f"{STOCK_CACHE_KEY_PREFIX}:{product_id}:{variant_part}:v1"


class RedisStockCache:
    """Cache stock snapshots without making Redis part of correctness."""

    def __init__(self, client: Redis, ttl_seconds: int) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    async def get_stock(
        self,
        product_id: UUID,
        variant_id: UUID | None,
    ) -> StockResponse | None:
        """Return a validated snapshot, treating Redis failures as misses."""
        key = stock_cache_key(product_id, variant_id)
        try:
            cached = await self._client.hgetall(key)
        except RedisError:
            self._record_error("read")
            return None

        if not cached:
            STOCK_CACHE_OPERATIONS.labels(operation="read", result="miss").inc()
            return None

        try:
            revision = int(cached["revision"])
            if revision < 1:
                raise ValueError("stock revision must be positive")
            stock = StockResponse.model_validate_json(cached["payload"])
            if stock.product_id != product_id or stock.variant_id != variant_id:
                raise ValueError("stock cache key does not match payload")
        except (KeyError, TypeError, ValueError, ValidationError):
            STOCK_CACHE_OPERATIONS.labels(operation="read", result="error").inc()
            _logger.warning(
                "Malformed stock cache value ignored",
                extra={"cache_operation": "read"},
            )
            await self._delete_malformed_value(key)
            return None

        STOCK_CACHE_OPERATIONS.labels(operation="read", result="hit").inc()
        return stock

    async def store_stock(
        self,
        stock: StockResponse,
        revision: int,
    ) -> StockCacheStoreResult:
        """Atomically store a snapshot unless Redis already has a newer revision."""
        key = stock_cache_key(stock.product_id, stock.variant_id)
        payload = stock.model_dump_json()
        try:
            stored = await self._client.eval(
                _STORE_IF_CURRENT_SCRIPT,
                1,
                key,
                revision,
                payload,
                self._ttl_seconds,
            )
        except RedisError:
            self._record_error("write")
            return StockCacheStoreResult.ERROR

        if int(stored) == 0:
            STOCK_CACHE_OPERATIONS.labels(operation="write", result="stale").inc()
            return StockCacheStoreResult.STALE

        STOCK_CACHE_OPERATIONS.labels(operation="write", result="success").inc()
        return StockCacheStoreResult.STORED

    async def _delete_malformed_value(self, key: str) -> None:
        try:
            await self._client.delete(key)
        except RedisError:
            self._record_error("invalidate")
            return
        STOCK_CACHE_OPERATIONS.labels(operation="invalidate", result="success").inc()

    @staticmethod
    def _record_error(operation: str) -> None:
        STOCK_CACHE_OPERATIONS.labels(operation=operation, result="error").inc()
        _logger.warning(
            "Stock cache operation failed",
            extra={"cache_operation": operation},
            exc_info=True,
        )


_settings = get_settings()
redis_client = Redis.from_url(
    _settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=_settings.redis_socket_timeout_seconds,
    socket_timeout=_settings.redis_socket_timeout_seconds,
)
stock_cache = RedisStockCache(redis_client, _settings.stock_cache_ttl_seconds)
