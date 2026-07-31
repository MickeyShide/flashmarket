"""Pydantic request and response schemas for the Orders API."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from orders.domain.entities import DiscountType, OrderStatus, PromocodeStatus

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
    promocode: str | None = Field(default=None, max_length=50)


class OrderListParams(BaseModel):
    """Query-string parameters for listing a user's orders."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class CreatePromocodeRequest(BaseModel):
    """Payload for creating a new promocode."""

    code: str = Field(min_length=1, max_length=50)
    discount_type: DiscountType
    discount_value: Decimal = Field(gt=0)
    currency: str = Field(default="RUB", min_length=3, max_length=3)
    min_order_amount: Decimal | None = Field(default=None, ge=0)
    max_discount_amount: Decimal | None = Field(default=None, ge=0)
    max_uses: int | None = Field(default=None, ge=1)
    max_uses_per_user: int = Field(default=1, ge=1)
    starts_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def validate_promocode_fields(self) -> "CreatePromocodeRequest":
        if self.expires_at <= self.starts_at:
            raise ValueError("expires_at must be after starts_at")
        if self.discount_type == DiscountType.PERCENTAGE and (
            self.discount_value <= 0 or self.discount_value > 100
        ):
            raise ValueError("PERCENTAGE discount_value must be between 0 and 100")
        return self


class UpdatePromocodeRequest(BaseModel):
    """Payload for updating an existing promocode."""

    discount_type: DiscountType | None = None
    discount_value: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    min_order_amount: Decimal | None = Field(default=None, ge=0)
    max_discount_amount: Decimal | None = Field(default=None, ge=0)
    max_uses: int | None = Field(default=None, ge=1)
    max_uses_per_user: int | None = Field(default=None, ge=1)
    status: PromocodeStatus | None = None
    starts_at: datetime | None = None
    expires_at: datetime | None = None


class ValidatePromocodeRequest(BaseModel):
    """Payload for validating a promocode before order creation."""

    code: str = Field(min_length=1, max_length=50)
    user_id: uuid.UUID
    order_amount: Decimal = Field(gt=0)


class PromocodeListParams(BaseModel):
    """Query parameters for promocode listing."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class PromocodeResponse(BaseModel):
    """Public representation of a promocode."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    discount_type: DiscountType
    discount_value: Decimal
    currency: str
    min_order_amount: Decimal | None
    max_discount_amount: Decimal | None
    max_uses: int | None
    max_uses_per_user: int
    current_uses: int
    status: PromocodeStatus
    starts_at: datetime
    expires_at: datetime
    created_at: datetime


class PromocodeListResponse(BaseModel):
    """Paginated list of promocodes."""

    items: list[PromocodeResponse]
    total: int
    limit: int
    offset: int


class PromocodeValidationResponse(BaseModel):
    """Response payload for promocode validation."""

    valid: bool
    discount_amount: Decimal
    final_amount: Decimal
    error: str | None = None


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
    original_price: Decimal | None = None
    discount_amount: Decimal = Decimal("0")
    final_price: Decimal | None = None
    promocode_id: uuid.UUID | None = None
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
