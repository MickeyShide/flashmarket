"""Health check route."""

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health/ready", summary="Readiness probe")
async def health_ready() -> dict[str, Any]:
    """Return status ok for readiness probe."""
    return {"status": "ok"}
