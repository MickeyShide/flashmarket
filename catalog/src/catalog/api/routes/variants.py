"""API routes for managing product variants."""

from uuid import UUID

from fastapi import APIRouter, status

from catalog.api.dependencies import AdminPrincipal, VariantServiceDep
from catalog.application.schemas import (
    CreateVariantRequest,
    UpdateVariantRequest,
    VariantResponse,
)

router = APIRouter(prefix="/api/v1/products/{product_id}/variants", tags=["variants"])


@router.post(
    "/",
    response_model=VariantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a variant for a product",
)
async def create_variant(
    product_id: UUID,
    data: CreateVariantRequest,
    service: VariantServiceDep,
    admin: AdminPrincipal,
) -> VariantResponse:
    """Create a new variant option for a product."""
    variant = await service.create_variant(product_id, data)
    return VariantResponse.model_validate(variant)


@router.get(
    "/",
    response_model=list[VariantResponse],
    status_code=status.HTTP_200_OK,
    summary="List all variants of a product",
)
async def list_variants(
    product_id: UUID,
    service: VariantServiceDep,
) -> list[VariantResponse]:
    """List all variants associated with a product."""
    variants = await service.list_variants(product_id)
    return [VariantResponse.model_validate(v) for v in variants]


@router.get(
    "/{variant_id}",
    response_model=VariantResponse,
    status_code=status.HTTP_200_OK,
    summary="Get variant by ID",
)
async def get_variant(
    product_id: UUID,
    variant_id: UUID,
    service: VariantServiceDep,
) -> VariantResponse:
    """Get variant details by ID."""
    variant = await service.get_by_id(variant_id, product_id=product_id)
    return VariantResponse.model_validate(variant)


@router.patch(
    "/{variant_id}",
    response_model=VariantResponse,
    status_code=status.HTTP_200_OK,
    summary="Update variant",
)
async def update_variant(
    product_id: UUID,
    variant_id: UUID,
    data: UpdateVariantRequest,
    service: VariantServiceDep,
    admin: AdminPrincipal,
) -> VariantResponse:
    """Update fields of a variant."""
    variant = await service.update_variant(variant_id, data, product_id=product_id)
    return VariantResponse.model_validate(variant)


@router.delete(
    "/{variant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete variant",
)
async def delete_variant(
    product_id: UUID,
    variant_id: UUID,
    service: VariantServiceDep,
    admin: AdminPrincipal,
) -> None:
    """Delete a variant option."""
    await service.delete_variant(variant_id, product_id=product_id)
