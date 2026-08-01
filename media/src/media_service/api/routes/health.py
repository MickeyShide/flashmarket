"""Liveness and dependency readiness."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from media_service.api.dependencies import DbSession, StorageDep

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def health_ready(db: DbSession, storage: StorageDep) -> dict[str, Any]:
    try:
        await db.execute(text("SELECT 1"))
        await storage.check_bucket()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Media dependencies unavailable",
        ) from exc
    return {"status": "ok", "database": "ok", "storage": "ok"}
