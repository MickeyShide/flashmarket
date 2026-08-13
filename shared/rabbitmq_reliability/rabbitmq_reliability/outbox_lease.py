"""Short database leases for crash-recoverable transactional outbox relays."""

# SQLAlchemy models are accepted structurally: each service owns its ORM base.
# mypy: disable-error-code="explicit-any,no-any-return"

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .delivery import sanitize_error
from .outbox import retry_backoff_seconds

logger = logging.getLogger(__name__)


async def claim_outbox_event(
    session_factory: async_sessionmaker[AsyncSession],
    model: Any,
    now: datetime,
    *,
    lease_seconds: int = 30,
) -> tuple[Any, uuid.UUID] | None:
    """Atomically lease the oldest due event and release the row lock."""
    token = uuid.uuid7()
    status_column = getattr(model, "status", None)
    pending_filter = (
        status_column.in_(["pending", "failed"])
        if status_column is not None
        else model.published_at.is_(None)
    )
    order_column = getattr(model, "created_at", None)
    if order_column is None:
        order_column = model.occurred_at
    async with session_factory() as db, db.begin():
        event = await db.scalar(
            select(model)
            .where(pending_filter)
            .where(or_(model.next_attempt_at.is_(None), model.next_attempt_at <= now))
            .where(or_(model.claimed_until.is_(None), model.claimed_until <= now))
            .order_by(order_column)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if event is None:
            return None
        event.claim_token = token
        event.claimed_until = now + timedelta(seconds=lease_seconds)
    return event, token


async def record_outbox_result(
    session_factory: async_sessionmaker[AsyncSession],
    model: Any,
    event_id: uuid.UUID,
    token: uuid.UUID,
    now: datetime,
    error: Exception | None,
) -> bool:
    """Record the result only when the caller still owns the event lease."""
    async with session_factory() as db, db.begin():
        event = await db.scalar(
            select(model).where(model.id == event_id, model.claim_token == token).with_for_update()
        )
        if event is None:
            logger.warning("Outbox claim expired before result was recorded: %s", event_id)
            return False
        event.attempts = (event.attempts or 0) + 1
        event.claim_token = None
        event.claimed_until = None
        if error is None:
            if hasattr(event, "status"):
                event.status = "published"
            event.published_at = now
            event.next_attempt_at = None
            event.last_error = None
        else:
            if hasattr(event, "status"):
                event.status = "failed"
            event.published_at = None
            event.next_attempt_at = now + timedelta(seconds=retry_backoff_seconds(event.attempts))
            event.last_error = sanitize_error(error)
    return True
