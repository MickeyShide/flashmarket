"""Pydantic request and response schemas for the Inventory API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from inventory.domain.entities import ReservationStatus

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class StockCreateRequest(BaseModel):
    """Payload for initializing stock for a product."""

    product_id: uuid.UUID
    total: int = Field(ge=0, le=1_000_000)


class StockUpdateRequest(BaseModel):
    """Payload for changing the total stock of a product."""

    total: int = Field(ge=0, le=1_000_000)


class ReserveRequest(BaseModel):
    """Payload for reserving stock for a user."""

    user_id: uuid.UUID
    quantity: int = Field(default=1, ge=1, le=10_000)
    order_id: uuid.UUID | None = None


class CommitRequest(BaseModel):
    """Payload for committing a reservation to a sale."""

    order_id: uuid.UUID


class ReleaseRequest(BaseModel):
    """Payload for manually releasing a reservation."""

    order_id: uuid.UUID


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class StockResponse(BaseModel):
    """Public representation of product stock."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    total: int
    available: int
    reserved: int
    sold: int
    created_at: datetime
    updated_at: datetime


class ReservationResponse(BaseModel):
    """Public representation of a reservation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stock_id: uuid.UUID
    user_id: uuid.UUID
    order_id: uuid.UUID | None
    quantity: int
    status: ReservationStatus
    expires_at: datetime
    created_at: datetime


class ReservationResult(BaseModel):
    """Result of a successful reservation."""

    reservation: ReservationResponse
    stock: StockResponse


class ErrorDetail(BaseModel):
    """Structured error information."""

    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: ErrorDetail
