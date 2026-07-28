import uuid
from datetime import datetime
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from redis.exceptions import RedisError

from auth_service.config import get_settings
from auth_service.time import as_utc, utc_now

settings = get_settings()
redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


class CacheUnavailableError(RuntimeError):
    pass


def get_cache() -> Redis:
    """Return the shared Redis client."""
    return redis_client


Cache = Annotated[Redis, Depends(get_cache)]


def session_cache_key(session_id: uuid.UUID) -> str:
    """Build the Redis key that marks a session as active."""
    return f"auth:session:{session_id}"


def session_touch_key(session_id: uuid.UUID) -> str:
    """Build the Redis key used to throttle session touch updates."""
    return f"auth:session-touch:{session_id}"


async def activate_session(
    cache: Redis,
    *,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
    expires_at: datetime,
) -> None:
    """Mark a session as active in Redis until its expiry."""
    ttl = max(1, int((as_utc(expires_at) - utc_now()).total_seconds()))
    try:
        await cache.set(
            session_cache_key(session_id),
            str(user_id),
            ex=ttl,
        )
    except RedisError as exc:
        raise CacheUnavailableError("Redis session store is unavailable") from exc


async def is_session_active(
    cache: Redis,
    *,
    session_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    """Check whether Redis still marks a session as active."""
    try:
        cached_user_id = await cache.get(session_cache_key(session_id))
    except RedisError as exc:
        raise CacheUnavailableError("Redis session store is unavailable") from exc
    return cached_user_id == str(user_id)


async def deactivate_session(cache: Redis, session_id: uuid.UUID) -> None:
    """Remove one session from Redis immediately."""
    try:
        await cache.delete(
            session_cache_key(session_id),
            session_touch_key(session_id),
        )
    except RedisError as exc:
        raise CacheUnavailableError("Redis session store is unavailable") from exc


async def deactivate_sessions(cache: Redis, session_ids: list[uuid.UUID]) -> None:
    """Remove several sessions from Redis immediately."""
    if not session_ids:
        return
    try:
        keys = [
            key
            for session_id in session_ids
            for key in (session_cache_key(session_id), session_touch_key(session_id))
        ]
        await cache.delete(*keys)
    except RedisError as exc:
        raise CacheUnavailableError("Redis session store is unavailable") from exc


async def should_touch_session(
    cache: Redis,
    *,
    session_id: uuid.UUID,
    interval_seconds: int,
) -> bool:
    """Decide whether a session last-seen timestamp should be updated."""
    try:
        created = await cache.set(
            session_touch_key(session_id),
            "1",
            ex=interval_seconds,
            nx=True,
        )
    except RedisError as exc:
        raise CacheUnavailableError("Redis session store is unavailable") from exc
    return bool(created)
