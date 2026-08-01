"""Tests for category cache behavior and its service integration."""

import uuid
from typing import cast
from unittest.mock import AsyncMock

import pytest
from fakeredis.aioredis import FakeRedis
from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from catalog.application.schemas import CategoryTreeNode, CreateCategoryRequest
from catalog.application.services.category import CategoryService
from catalog.config import Settings
from catalog.infrastructure.category_cache import (
    CATEGORY_TREE_CACHE_KEY,
    RedisCategoryTreeCache,
)
from catalog.infrastructure.models import CategoryModel


def _tree() -> list[CategoryTreeNode]:
    return [
        CategoryTreeNode(
            id=uuid.uuid4(),
            name="Shoes",
            slug="shoes",
        )
    ]


async def test_redis_cache_round_trip_and_ttl() -> None:
    client = FakeRedis(decode_responses=True)
    cache = RedisCategoryTreeCache(cast(Redis, client), ttl_seconds=60)
    tree = _tree()

    await cache.store_tree(tree)

    assert await cache.get_tree() == tree
    ttl = await client.ttl(CATEGORY_TREE_CACHE_KEY)
    assert 0 < ttl <= 60
    await client.aclose()


async def test_malformed_cache_value_is_deleted() -> None:
    client = FakeRedis(decode_responses=True)
    cache = RedisCategoryTreeCache(cast(Redis, client), ttl_seconds=60)
    await client.set(CATEGORY_TREE_CACHE_KEY, "not-json")

    assert await cache.get_tree() is None
    assert await client.exists(CATEGORY_TREE_CACHE_KEY) == 0
    await client.aclose()


class _FailingRedis:
    async def get(self, _key: str) -> str | None:
        raise RedisError("unavailable")

    async def set(self, *_args: object, **_kwargs: object) -> None:
        raise RedisError("unavailable")

    async def delete(self, _key: str) -> None:
        raise RedisError("unavailable")


async def test_redis_failures_are_fail_open() -> None:
    cache = RedisCategoryTreeCache(
        cast(Redis, _FailingRedis()),
        ttl_seconds=60,
    )

    assert await cache.get_tree() is None
    await cache.store_tree(_tree())
    await cache.invalidate_tree()


async def test_cache_failure_does_not_block_database_fallback() -> None:
    session = AsyncMock()
    repository = AsyncMock()
    repository.list_all.return_value = [
        CategoryModel(
            id=uuid.uuid4(),
            name="Shoes",
            slug="shoes",
            parent_id=None,
        )
    ]
    cache = RedisCategoryTreeCache(
        cast(Redis, _FailingRedis()),
        ttl_seconds=60,
    )
    service = CategoryService(session, repository, cache)

    tree = await service.get_category_tree()

    assert [node.slug for node in tree] == ["shoes"]


async def test_service_cache_hit_skips_repository() -> None:
    session = AsyncMock()
    repository = AsyncMock()
    cache = AsyncMock()
    tree = _tree()
    cache.get_tree.return_value = tree
    service = CategoryService(session, repository, cache)

    assert await service.get_category_tree() == tree
    repository.list_all.assert_not_awaited()
    cache.store_tree.assert_not_awaited()


async def test_service_cache_miss_builds_and_stores_tree() -> None:
    session = AsyncMock()
    repository = AsyncMock()
    cache = AsyncMock()
    cache.get_tree.return_value = None
    category = CategoryModel(
        id=uuid.uuid4(),
        name="Shoes",
        slug="shoes",
        parent_id=None,
    )
    repository.list_all.return_value = [category]
    service = CategoryService(session, repository, cache)

    tree = await service.get_category_tree()

    assert [node.slug for node in tree] == ["shoes"]
    cache.store_tree.assert_awaited_once_with(tree)


async def test_successful_creation_invalidates_after_commit() -> None:
    events: list[str] = []
    session = AsyncMock()
    session.commit.side_effect = lambda: events.append("commit")
    repository = AsyncMock()
    repository.slug_exists.return_value = False
    cache = AsyncMock()
    cache.invalidate_tree.side_effect = lambda: events.append("invalidate")
    service = CategoryService(session, repository, cache)

    await service.create_category(CreateCategoryRequest(name="Shoes", slug="shoes"))

    assert events == ["commit", "invalidate"]


async def test_cache_invalidation_failure_does_not_block_creation() -> None:
    session = AsyncMock()
    repository = AsyncMock()
    repository.slug_exists.return_value = False
    cache = RedisCategoryTreeCache(
        cast(Redis, _FailingRedis()),
        ttl_seconds=60,
    )
    service = CategoryService(session, repository, cache)

    category = await service.create_category(CreateCategoryRequest(name="Shoes", slug="shoes"))

    assert category.slug == "shoes"


async def test_failed_creation_does_not_invalidate() -> None:
    session = AsyncMock()
    session.commit.side_effect = RuntimeError("database unavailable")
    repository = AsyncMock()
    repository.slug_exists.return_value = False
    cache = AsyncMock()
    service = CategoryService(session, repository, cache)

    with pytest.raises(RuntimeError, match="database unavailable"):
        await service.create_category(CreateCategoryRequest(name="Shoes", slug="shoes"))

    cache.invalidate_tree.assert_not_awaited()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("category_cache_ttl_seconds", 0),
        ("redis_socket_timeout_seconds", 0),
    ],
)
def test_cache_settings_must_be_positive(field: str, value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(**{field: value})
