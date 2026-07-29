"""Health-check endpoint."""

from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from notifications.api.dependencies import DbSession

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
    except SQLAlchemyError:
        return dict(status="unavailable")
    return dict(status="ok")
