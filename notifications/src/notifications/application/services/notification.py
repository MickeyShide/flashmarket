"""Notification application service."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from notifications.application.schemas import CreateNotificationRequest
from notifications.domain.entities import NotificationEventType, NotificationStatus
from notifications.domain.exceptions import InvalidNotificationState, NotificationNotFound
from notifications.infrastructure.models import NotificationModel
from notifications.infrastructure.repositories.notification import (
    NotificationRepository,
    OutboxRepository,
)


def utc_now() -> datetime:
    """Return the current UTC-aware datetime."""
    return datetime.now(UTC)


class NotificationService:
    """Orchestrates notification creation and delivery."""

    def __init__(
        self,
        session: AsyncSession,
        notification_repo: NotificationRepository,
        outbox_repo: OutboxRepository,
    ) -> None:
        self._session = session
        self._notification_repo = notification_repo
        self._outbox_repo = outbox_repo

    async def create_notification(self, data: CreateNotificationRequest) -> NotificationModel:
        """Persist a notification to be delivered."""
        notification = NotificationModel(
            user_id=data.user_id,
            channel=data.channel,
            subject=data.subject,
            body=data.body,
            recipient=data.recipient,
            status=NotificationStatus.PENDING,
        )
        await self._notification_repo.create(notification)
        await self._session.commit()
        await self._session.refresh(notification)
        return notification

    async def mark_sent(self, notification_id: uuid.UUID) -> NotificationModel:
        """Mark a notification as sent and emit an event."""
        notification = await self._notification_repo.get_by_id(notification_id)
        if notification is None:
            raise NotificationNotFound
        if notification.status != NotificationStatus.PENDING:
            raise InvalidNotificationState("Notification is not pending")

        notification.status = NotificationStatus.SENT
        notification.sent_at = utc_now()
        await self._notification_repo.update(notification)

        payload = {
            "notification_id": str(notification.id),
            "user_id": str(notification.user_id),
            "channel": str(notification.channel),
            "recipient": notification.recipient,
            "subject": notification.subject,
        }
        await self._outbox_repo.add(
            NotificationEventType.NOTIFICATION_SENT,
            json.dumps(payload, separators=(",", ":")),
        )

        await self._session.commit()
        await self._session.refresh(notification)
        return notification

    async def mark_failed(
        self,
        notification_id: uuid.UUID,
        reason: str,
    ) -> NotificationModel:
        """Mark a notification as failed."""
        notification = await self._notification_repo.get_by_id(notification_id)
        if notification is None:
            raise NotificationNotFound

        notification.status = NotificationStatus.FAILED
        notification.attempts += 1
        notification.last_error = reason
        await self._notification_repo.update(notification)
        await self._session.commit()
        await self._session.refresh(notification)
        return notification

    async def get_notification(self, notification_id: uuid.UUID) -> NotificationModel:
        """Return a notification by id."""
        notification = await self._notification_repo.get_by_id(notification_id)
        if notification is None:
            raise NotificationNotFound
        return notification

    async def list_user_notifications(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[NotificationModel], int]:
        """Return a paginated list of a user's notifications."""
        items = await self._notification_repo.list_by_user(
            user_id, limit=limit, offset=offset
        )
        total = await self._notification_repo.count_by_user(user_id)
        return list(items), total
