"""Pydantic request and response schemas for the Notifications API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from notifications.domain.entities import NotificationChannel, NotificationStatus


class CreateNotificationRequest(BaseModel):
    """Payload for creating a notification."""

    user_id: uuid.UUID
    channel: NotificationChannel = NotificationChannel.EMAIL
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=10000)
    recipient: str = Field(min_length=1, max_length=255)


class NotificationListParams(BaseModel):
    """Query-string parameters for listing a user's notifications."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class NotificationResponse(BaseModel):
    """Public representation of a notification."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    channel: NotificationChannel
    subject: str
    body: str
    recipient: str
    status: NotificationStatus
    attempts: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None


class NotificationListResponse(BaseModel):
    """Paginated notification listing."""

    items: list[NotificationResponse]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    """Structured error information."""

    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: ErrorDetail
