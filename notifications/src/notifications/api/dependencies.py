"""FastAPI dependency injection wiring."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from notifications.application.services.notification import NotificationService
from notifications.infrastructure.database import get_db
from notifications.infrastructure.repositories.notification import (
    NotificationRepository,
    OutboxRepository,
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_notification_service(db: DbSession) -> NotificationService:
    """Build a notification service for the current request."""
    return NotificationService(
        session=db,
        notification_repo=NotificationRepository(db),
        outbox_repo=OutboxRepository(db),
    )


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]
