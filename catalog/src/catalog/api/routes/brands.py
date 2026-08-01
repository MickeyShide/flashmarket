"""Brand API endpoints (public)."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status

from catalog.api.dependencies import AdminPrincipal, BrandServiceDep
from catalog.application.schemas import (
    BrandResponse,
    CreateBrandRequest,
    ErrorResponse,
)
from catalog.infrastructure.models import BrandModel

router = APIRouter(prefix="/api/v1/brands", tags=["brands"])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Not Found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    422: {"model": ErrorResponse, "description": "Validation Error"},
}


def _brand_to_response(brand: BrandModel) -> BrandResponse:
    """Map an ORM brand to a response schema."""
    return BrandResponse(
        id=brand.id,
        name=brand.name,
        slug=brand.slug,
        description=brand.description,
        logo_url=brand.logo_url,
        created_at=brand.created_at,
    )


@router.post(
    "",
    response_model=BrandResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
    summary="Create a brand",
)
async def create_brand(
    data: CreateBrandRequest,
    service: BrandServiceDep,
    admin: AdminPrincipal,
) -> BrandResponse:
    """Create a new brand."""
    brand = await service.create_brand(data)
    return _brand_to_response(brand)


@router.get(
    "",
    response_model=list[BrandResponse],
    summary="List all brands",
)
async def list_brands(
    service: BrandServiceDep,
) -> list[BrandResponse]:
    """Return all registered brands ordered by name."""
    brands = await service.list_brands()
    return [_brand_to_response(b) for b in brands]


@router.get(
    "/{slug_or_id}",
    response_model=BrandResponse,
    responses=ERROR_RESPONSES,
    summary="Get brand by slug or UUID",
)
async def get_brand(
    slug_or_id: str,
    service: BrandServiceDep,
) -> BrandResponse:
    """Fetch brand details by unique slug or UUID."""
    try:
        brand_id = uuid.UUID(slug_or_id)
        brand = await service.get_by_id(brand_id)
    except ValueError:
        brand = await service.get_by_slug(slug_or_id)

    return _brand_to_response(brand)
