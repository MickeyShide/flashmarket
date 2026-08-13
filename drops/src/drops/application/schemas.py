"""Pydantic schemas for request validation and response serialization."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from drops.domain.entities import DropStatus


# Request models
class CreateDropRequest(BaseModel):
    """Payload for creating a new drop."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = Field(default="")
    cover_image: str | None = Field(default=None, max_length=2048)
    starts_at: datetime
    ends_at: datetime
    max_per_user: int = Field(default=1, ge=1, le=100)
    payment_timeout_seconds: int = Field(default=300, ge=60, le=3600)

    @model_validator(mode="after")
    def validate_time_range(self) -> CreateDropRequest:
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class UpdateDropRequest(BaseModel):
    """Payload for updating an existing drop."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(
        default=None, min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    description: str | None = None
    cover_image: str | None = Field(default=None, max_length=2048)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    max_per_user: int | None = Field(default=None, ge=1, le=100)
    payment_timeout_seconds: int | None = Field(default=None, ge=60, le=3600)

    @model_validator(mode="after")
    def validate_time_range(self) -> UpdateDropRequest:
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class AddDropItemRequest(BaseModel):
    """Payload for adding a product item to a drop."""

    product_id: uuid.UUID
    sort_order: int = Field(default=0, ge=0)


class DropListParams(BaseModel):
    """Query parameters for drop listing."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    status: DropStatus | None = None


# Response models
class DropItemResponse(BaseModel):
    """Product item in a drop."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    sort_order: int


class DropResponse(BaseModel):
    """Drop response payload."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str
    cover_image: str | None
    status: DropStatus
    starts_at: datetime
    ends_at: datetime
    max_per_user: int
    payment_timeout_seconds: int
    items: list[DropItemResponse]
    created_at: datetime
    updated_at: datetime


class DropListResponse(BaseModel):
    """Paginated list of drops response payload."""

    items: list[DropResponse]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    """Standardized error payload format."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Root error wrapper."""

    error: ErrorDetail
