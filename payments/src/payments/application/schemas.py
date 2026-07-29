"""Pydantic request and response schemas for the Payments API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from payments.domain.entities import PaymentStatus


class CreatePaymentRequest(BaseModel):
    """Payload for creating a payment for an order."""

    order_id: uuid.UUID
    user_id: uuid.UUID
    amount: int = Field(gt=0, le=10_000_000_000)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    provider: str = Field(default="mock", min_length=1, max_length=64)


class PaymentListParams(BaseModel):
    """Query-string parameters for listing a user's payments."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class PaymentResponse(BaseModel):
    """Public representation of a payment."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    user_id: uuid.UUID
    amount: int
    currency: str
    provider: str
    status: PaymentStatus
    external_id: str | None
    created_at: datetime
    updated_at: datetime


class PaymentListResponse(BaseModel):
    """Paginated payment listing."""

    items: list[PaymentResponse]
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
