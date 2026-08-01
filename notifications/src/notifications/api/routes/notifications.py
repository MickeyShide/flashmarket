"""Notification API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from notifications.api.dependencies import (
    AdminPrincipal,
    CurrentPrincipal,
    get_notification_service,
)
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
    admin: AdminPrincipal,
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
    principal: CurrentPrincipal,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    """Return a single notification by id."""
    notification = await service.get_notification(notification_id)
    if principal.role != "ADMIN" and notification.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view another user's notification",
        )
    return _notification_response(notification)


@router.get(
    "/users/{user_id}",
    response_model=NotificationListResponse,
    summary="List user notifications",
)
async def list_notifications(
    user_id: UUID,
    principal: CurrentPrincipal,
    params: NotificationListParams = Depends(),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    """Return paginated notifications for a user."""
    if principal.role != "ADMIN" and user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot list another user's notifications",
        )
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
    principal: CurrentPrincipal,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    """Mark a notification as sent and emit an event."""
    n = await service.get_notification(notification_id)
    if principal.role != "ADMIN" and n.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot send notification belonging to another user",
        )
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
    admin: AdminPrincipal,
    service: NotificationService = Depends(get_notification_service),
) -> NotificationResponse:
    """Mark a notification as failed."""
    notification = await service.mark_failed(notification_id, reason)
    return _notification_response(notification)
