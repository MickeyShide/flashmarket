import hashlib

from fastapi import HTTPException, status
from redis.asyncio import Redis
from redis.exceptions import RedisError

from auth_service.config import get_settings
from auth_service.observability import RATE_LIMIT_REJECTIONS


def _rate_limit_key(scope: str, identity: str) -> str:
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    return f"auth:rate:{scope}:{digest}"


async def enforce_rate_limit(
    cache: Redis,
    *,
    scope: str,
    identity: str,
    limit: int,
    window_seconds: int,
) -> None:
    if not get_settings().rate_limit_enabled:
        return

    key = _rate_limit_key(scope, identity)
    try:
        async with cache.pipeline(transaction=True) as pipeline:
            pipeline.incr(key)
            pipeline.expire(key, window_seconds, nx=True)
            pipeline.ttl(key)
            count, _, ttl = await pipeline.execute()
    except RedisError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Rate limiter is unavailable",
        ) from exc

    if int(count) > limit:
        retry_after = max(1, int(ttl))
        RATE_LIMIT_REJECTIONS.labels(scope=scope).inc()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests",
            headers={"Retry-After": str(retry_after)},
        )
