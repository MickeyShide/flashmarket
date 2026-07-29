"""Notification API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from notifications.api.dependencies import get_notification_service
from notifications.application.schemas import (
    CreateNotificationRequest,
    NotificationListParams,
    NotificationListResponse,
    NotificationResponse,
)
from notifications.application.services.notification import NotificationService
from notifications.infrastructure.models import NotificationModel

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def _notification_response(notification: NotificationModel) -> NotificationResponse:
    return NotificationResponse.model_validate(notification)


@router.post(
    "",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a notification",
)
async def create_notification(
    data: CreateNotificationRequest,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    """Persist a notification to be delivered."""
    notification = await service.create_notification(data)
    return _notification_response(notification)


@router.get(
    "/{notification_id}",
    response_model=NotificationResponse,
    summary="Get a notification",
)
async def get_notification(
    notification_id: UUID,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    """Return a single notification by id."""
    notification = await service.get_notification(notification_id)
    return _notification_response(notification)


@router.get(
    "/users/{user_id}",
    response_model=NotificationListResponse,
    summary="List user notifications",
)
async def list_notifications(
    user_id: UUID,
    params: NotificationListParams = Depends(),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    """Return paginated notifications for a user."""
    items, total = await service.list_user_notifications(
        user_id,
        limit=params.limit,
        offset=params.offset,
    )
    return NotificationListResponse(
        items=[_notification_response(item) for item in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


@router.post(
    "/{notification_id}/send",
    response_model=NotificationResponse,
    summary="Mark notification as sent",
)
async def send_notification(
    notification_id: UUID,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    """Mark a notification as sent and emit an event."""
    notification = await service.mark_sent(notification_id)
    return _notification_response(notification)


@router.post(
    "/{notification_id}/fail",
    response_model=NotificationResponse,
    summary="Mark notification delivery as failed",
)
async def fail_notification(
    notification_id: UUID,
    reason: str,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    """Mark a notification as failed."""
    notification = await service.mark_failed(notification_id, reason)
    return _notification_response(notification)
