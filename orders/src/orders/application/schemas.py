"""Pydantic request and response schemas for the Orders API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from orders.domain.entities import OrderStatus

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateOrderRequest(BaseModel):
    """Payload for creating an order from a reservation."""

    user_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str = Field(min_length=1, max_length=255)
    price: int = Field(gt=0, le=10_000_000_000)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    quantity: int = Field(default=1, ge=1, le=10_000)
    reservation_id: uuid.UUID


class OrderListParams(BaseModel):
    """Query-string parameters for listing a user's orders."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class OrderResponse(BaseModel):
    """Public representation of an order."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    product_id: uuid.UUID
    product_name: str
    price: int
    currency: str
    quantity: int
    status: OrderStatus
    reservation_id: uuid.UUID
    payment_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    """Paginated order listing."""

    items: list[OrderResponse]
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
