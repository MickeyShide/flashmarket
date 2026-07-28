from fastapi import APIRouter, HTTPException, status
from redis.exceptions import RedisError
from sqlalchemy import text

from auth_service.api.dependencies import DbSession
from auth_service.cache import Cache

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    """Report that the process is running."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness(db: DbSession, cache: Cache) -> dict[str, str]:
    """Check that database and Redis dependencies are reachable."""
    try:
        await db.execute(text("SELECT 1"))
        await cache.ping()
    except (Exception, RedisError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A required dependency is unavailable",
        ) from exc
    return {"status": "ok"}
