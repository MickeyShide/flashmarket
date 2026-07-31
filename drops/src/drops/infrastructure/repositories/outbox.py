"""Outbox repository for persisting domain events."""

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from drops.infrastructure.models import OutboxEventModel


class OutboxRepository:
    """Handles persistence of outbox events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_event(self, event_type: str, payload: dict[str, Any]) -> OutboxEventModel:
        """Create a pending outbox event."""
        event = OutboxEventModel(
            event_type=event_type,
            payload=json.dumps(payload),
            status="pending",
        )
        self._session.add(event)
        await self._session.flush()
        return event
