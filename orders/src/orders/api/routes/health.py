"""Health-check endpoint."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from orders.api.dependencies import DbSession

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/ready",
    response_model=dict[str, str],
    summary="Readiness probe",
    description="Returns 200 when the database is reachable.",
    responses={503: {"description": "Database unavailable"}},
)
async def readiness(db: DbSession) -> dict[str, str]:
    """Report service readiness by pinging the database."""
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc
    return {"status": "ok"}
