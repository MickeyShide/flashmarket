"""Pydantic schemas for request validation and response serialization."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# Request models
class AddToWishlistRequest(BaseModel):
    """Payload for adding a product to wishlist."""

    product_id: uuid.UUID


class WishlistListParams(BaseModel):
    """Query parameters for pagination."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class CheckWishlistRequest(BaseModel):
    """Payload for batch checking if products are in user's wishlist."""

    product_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)


# Response models
class WishlistItemResponse(BaseModel):
    """Item in wishlist."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    product_id: uuid.UUID
    created_at: datetime


class WishlistListResponse(BaseModel):
    """Paginated list of wishlist items."""

    items: list[WishlistItemResponse]
    total: int
    limit: int
    offset: int


class WishlistCheckResponse(BaseModel):
    """Response containing list of product IDs currently in wishlist."""

    product_ids: list[uuid.UUID]


class ErrorDetail(BaseModel):
    """Standardized error payload format."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Root error wrapper."""

    error: ErrorDetail
