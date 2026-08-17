"""One-shot Auth maintenance operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, cast

from sqlalchemy import delete, or_
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from auth_service.config import get_settings
from auth_service.database import SessionFactory
from auth_service.models import AuditEvent, LoginSession, OutboxEvent, RefreshToken
from auth_service.time import utc_now


@dataclass(frozen=True, slots=True)
class CleanupCounts:
    sessions: int
    refresh_tokens: int
    audit_events: int
    outbox_events: int


async def cleanup_expired_data(
    session_factory: async_sessionmaker[AsyncSession] = SessionFactory,
    *,
    now: datetime | None = None,
) -> CleanupCounts:
    """Delete retained expired Auth data in one transaction."""
    settings = get_settings()
    current_time = now or utc_now()
    expired_cutoff = current_time - timedelta(days=settings.expired_data_retention_days)
    audit_cutoff = current_time - timedelta(days=settings.audit_retention_days)

    async with session_factory() as db:
        session_result = await db.execute(
            delete(LoginSession).where(
                or_(
                    LoginSession.expires_at < expired_cutoff,
                    LoginSession.revoked_at < expired_cutoff,
                )
            )
        )
        refresh_result = await db.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < expired_cutoff)
        )
        audit_result = await db.execute(
            delete(AuditEvent).where(AuditEvent.created_at < audit_cutoff)
        )
        outbox_result = await db.execute(
            delete(OutboxEvent).where(OutboxEvent.published_at < expired_cutoff)
        )
        await db.commit()

    return CleanupCounts(
        sessions=cast(CursorResult[Any], session_result).rowcount,
        refresh_tokens=cast(CursorResult[Any], refresh_result).rowcount,
        audit_events=cast(CursorResult[Any], audit_result).rowcount,
        outbox_events=cast(CursorResult[Any], outbox_result).rowcount,
    )
