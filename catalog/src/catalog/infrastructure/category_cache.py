"""Fail-open Redis cache for the public category tree."""

import logging

from pydantic import TypeAdapter, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from catalog.application.schemas import CategoryTreeNode
from catalog.config import get_settings
from catalog.observability import CATEGORY_CACHE_OPERATIONS

CATEGORY_TREE_CACHE_KEY = "catalog:categories:tree:v1"

_category_tree_adapter = TypeAdapter(list[CategoryTreeNode])
_logger = logging.getLogger("catalog.cache")

_settings = get_settings()
redis_client = Redis.from_url(
    _settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=_settings.redis_socket_timeout_seconds,
    socket_timeout=_settings.redis_socket_timeout_seconds,
)


class RedisCategoryTreeCache:
    """Store and retrieve the category tree while treating Redis as optional."""

    def __init__(self, client: Redis, ttl_seconds: int) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    async def get_tree(self) -> list[CategoryTreeNode] | None:
        """Return a validated cached tree, falling back to a miss on errors."""
        try:
            cached = await self._client.get(CATEGORY_TREE_CACHE_KEY)
        except RedisError:
            self._record_error("read")
            return None

        if cached is None:
            CATEGORY_CACHE_OPERATIONS.labels(operation="read", result="miss").inc()
            return None

        try:
            tree = _category_tree_adapter.validate_json(cached)
        except ValidationError, ValueError, TypeError:
            CATEGORY_CACHE_OPERATIONS.labels(operation="read", result="error").inc()
            _logger.warning(
                "Malformed category cache value ignored",
                extra={"cache_operation": "read"},
            )
            await self._delete_malformed_value()
            return None

        CATEGORY_CACHE_OPERATIONS.labels(operation="read", result="hit").inc()
        return tree

    async def store_tree(self, tree: list[CategoryTreeNode]) -> None:
        """Store a validated tree with a bounded TTL, ignoring Redis failures."""
        payload = _category_tree_adapter.dump_json(tree)
        try:
            await self._client.set(
                CATEGORY_TREE_CACHE_KEY,
                payload,
                ex=self._ttl_seconds,
            )
        except RedisError:
            self._record_error("write")
            return
        CATEGORY_CACHE_OPERATIONS.labels(operation="write", result="success").inc()

    async def invalidate_tree(self) -> None:
        """Delete the cached tree without failing the completed mutation."""
        try:
            await self._client.delete(CATEGORY_TREE_CACHE_KEY)
        except RedisError:
            self._record_error("invalidate")
            return
        CATEGORY_CACHE_OPERATIONS.labels(operation="invalidate", result="success").inc()

    async def _delete_malformed_value(self) -> None:
        try:
            await self._client.delete(CATEGORY_TREE_CACHE_KEY)
        except RedisError:
            self._record_error("invalidate")

    @staticmethod
    def _record_error(operation: str) -> None:
        CATEGORY_CACHE_OPERATIONS.labels(operation=operation, result="error").inc()
        _logger.warning(
            "Category cache operation failed",
            extra={"cache_operation": operation},
            exc_info=True,
        )


category_tree_cache = RedisCategoryTreeCache(
    client=redis_client,
    ttl_seconds=_settings.category_cache_ttl_seconds,
)
