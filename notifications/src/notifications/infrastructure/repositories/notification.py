"""Notification and outbox persistence operations."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.infrastructure.database import utc_now
from notifications.infrastructure.models import NotificationModel, OutboxEventModel


class NotificationRepository:
    """Data-access layer for notifications."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, notification: NotificationModel) -> NotificationModel:
        """Persist a new notification."""
        self._session.add(notification)
        await self._session.flush()
        return notification

    async def get_by_id(self, notification_id: UUID) -> NotificationModel | None:
        """Fetch a notification by primary key."""
        return await self._session.get(NotificationModel, notification_id)

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> Sequence[NotificationModel]:
        """Return a user's notifications ordered by creation time."""
        result = await self._session.scalars(
            select(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .order_by(NotificationModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.all()

    async def update(self, notification: NotificationModel) -> NotificationModel:
        """Flush pending attribute changes on a notification."""
        await self._session.flush()
        return notification


class OutboxRepository:
    """Transactional outbox persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event_type: str, payload: str) -> OutboxEventModel:
        """Persist an outbox event within the current transaction."""
        event = OutboxEventModel(event_type=event_type, payload=payload)
        self._session.add(event)
        await self._session.flush()
        return event

    async def list_pending(self, limit: int) -> Sequence[OutboxEventModel]:
        """Return pending outbox events for the relay worker."""
        result = await self._session.scalars(
            select(OutboxEventModel)
            .where(OutboxEventModel.status == "pending")
            .order_by(OutboxEventModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return result.all()

    async def mark_published(self, event: OutboxEventModel) -> OutboxEventModel:
        """Mark an outbox event as published."""
        event.status = "published"
        event.published_at = utc_now()
        await self._session.flush()
        return event

    async def mark_failed(self, event: OutboxEventModel) -> OutboxEventModel:
        """Mark an outbox event as failed."""
        event.status = "failed"
        event.published_at = None
        await self._session.flush()
        return event
