"""Transactional inbox helpers for at-least-once consumers."""

# Service-owned SQLAlchemy models intentionally use structural typing.
# mypy: disable-error-code="explicit-any"

from __future__ import annotations

import hashlib
from typing import Any

from aio_pika.abc import AbstractIncomingMessage
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


def delivery_identity(message: AbstractIncomingMessage, routing_key: str) -> str:
    """Return the producer event ID or a stable legacy-message fingerprint."""
    headers = getattr(message, "headers", None) or {}
    value = getattr(message, "message_id", None) or headers.get("event_id")
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if value:
        return str(value)[:128]
    digest = hashlib.sha256(routing_key.encode("utf-8") + b"\0" + message.body).hexdigest()
    return f"sha256:{digest}"


async def begin_event_once(
    session: AsyncSession,
    model: Any,
    *,
    event_id: str,
    routing_key: str,
) -> bool:
    """Reserve an inbox ID in a savepoint; return false for a committed duplicate."""
    try:
        async with session.begin_nested():
            session.add(model(event_id=event_id, routing_key=routing_key))
            await session.flush()
    except IntegrityError:
        return False
    return True
