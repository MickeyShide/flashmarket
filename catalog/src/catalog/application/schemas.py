"""Pydantic request and response schemas for the Catalog API."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from catalog.domain.entities import Currency, ProductStatus

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateCategoryRequest(BaseModel):
    """Payload for creating a new category."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    parent_id: uuid.UUID | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Trim a category name and reject whitespace-only values."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class CreateBrandRequest(BaseModel):
    """Payload for creating a new brand."""

    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str | None = None
    logo_url: str | None = Field(default=None, max_length=2048)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Trim a brand name and reject whitespace-only values."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class UpdateBrandRequest(BaseModel):
    """Partial update payload for a brand."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    logo_url: str | None = Field(default=None, max_length=2048)


class ImageInput(BaseModel):
    """Single image entry inside a product request."""

    url: str = Field(min_length=1, max_length=2048)
    sort_order: int = Field(default=0, ge=0)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """Reject image URLs that contain only whitespace."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("url must not be blank")
        return normalized


class CreateProductRequest(BaseModel):
    """Payload for creating a new product."""

    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    currency: Currency = Currency.RUB
    category_id: uuid.UUID
    brand_id: uuid.UUID | None = None
    cover_image: str | None = Field(default=None, max_length=2048)
    images: list[ImageInput] = Field(default_factory=list)
    status: ProductStatus = ProductStatus.HIDDEN

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        """Trim a product name and reject whitespace-only values."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class UpdateProductRequest(BaseModel):
    """Partial-update payload; explicitly supplied fields are applied."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    currency: Currency | None = None
    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    cover_image: str | None = Field(default=None, max_length=2048)
    images: list[ImageInput] | None = None
    status: ProductStatus | None = None

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        """Trim a supplied product name and reject blank values."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be blank")
        return normalized


class ProductListParams(BaseModel):
    """Query-string parameters for the product listing endpoint."""

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    brand_slug: str | None = None
    status: ProductStatus | None = None
    price_from: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    price_to: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    search: str | None = Field(default=None, max_length=255)
    sort_by: Literal["price", "name", "created_at", "relevance"] = "created_at"
    sort_order: Literal["asc", "desc"] = "desc"

    @field_validator("search")
    @classmethod
    def normalize_search(cls, value: str | None) -> str | None:
        """Normalize an optional text-search phrase."""
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def validate_price_range(self) -> Self:
        """Ensure the requested lower bound does not exceed the upper bound."""
        if self.price_from is not None and self.price_to is not None:
            if self.price_from > self.price_to:
                raise ValueError("price_from must not exceed price_to")
        return self


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class CategoryResponse(BaseModel):
    """Public representation of a category."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    parent_id: uuid.UUID | None
    created_at: datetime


class BrandResponse(BaseModel):
    """Public representation of a brand."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    logo_url: str | None
    created_at: datetime


class CategoryTreeNode(BaseModel):
    """Recursive node used when returning the full category tree."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    children: list[CategoryTreeNode] = Field(default_factory=list)


CategoryTreeNode.model_rebuild()


class ImageResponse(BaseModel):
    """Public representation of a product image."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    sort_order: int


class CreateVariantRequest(BaseModel):
    """Payload for creating a new product variant."""

    sku: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=20)
    color: str | None = Field(default=None, max_length=50)
    color_hex: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    material: str | None = Field(default=None, max_length=100)
    weight_grams: int | None = Field(default=None, ge=0)
    price_override: Decimal | None = Field(default=None, gt=0)
    is_active: bool = True
    sort_order: int = Field(default=0, ge=0)


class UpdateVariantRequest(BaseModel):
    """Payload for updating a product variant."""

    sku: str | None = Field(default=None, max_length=100)
    size: str | None = Field(default=None, max_length=20)
    color: str | None = Field(default=None, max_length=50)
    color_hex: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    material: str | None = Field(default=None, max_length=100)
    weight_grams: int | None = Field(default=None, ge=0)
    price_override: Decimal | None = Field(default=None, gt=0)
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


class VariantResponse(BaseModel):
    """Public representation of a product variant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    size: str | None
    color: str | None
    color_hex: str | None
    material: str | None
    weight_grams: int | None
    price_override: Decimal | None
    effective_price: Decimal
    is_active: bool
    sort_order: int
    created_at: datetime

    @model_validator(mode="before")
    @classmethod
    def compute_effective_price(cls, data: Any) -> Any:
        if hasattr(data, "price_override"):
            override = getattr(data, "price_override", None)
            product = getattr(data, "product", None)
            effective = (
                override
                if override is not None
                else (product.price if product is not None else Decimal("0"))
            )
            if isinstance(data, dict):
                data["effective_price"] = effective
            else:
                data.effective_price = effective
        elif isinstance(data, dict):
            if "effective_price" not in data:
                override = data.get("price_override")
                data["effective_price"] = override if override is not None else Decimal("0")
        return data


class ProductResponse(BaseModel):
    """Public representation of a product."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    name: str
    description: str
    price: Decimal
    currency: Currency
    status: ProductStatus
    category_id: uuid.UUID
    category_name: str
    brand_id: uuid.UUID | None = None
    brand_name: str | None = None
    cover_image: str | None
    images: list[ImageResponse]
    variants: list[VariantResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None


class ProductListResponse(BaseModel):
    """Paginated product listing."""

    items: list[ProductResponse]
    total: int
    limit: int
    offset: int


class HealthResponse(BaseModel):
    """Readiness probe response."""

    status: Literal["ok"]


# ---------------------------------------------------------------------------
# Error response models (for OpenAPI docs)
# ---------------------------------------------------------------------------


class ErrorDetail(BaseModel):
    """Structured error information."""

    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    error: ErrorDetail
