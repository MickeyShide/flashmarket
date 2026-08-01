"""Product API endpoints (public)."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query, status

from catalog.api.dependencies import AdminPrincipal, ProductServiceDep
from catalog.application.schemas import (
    CreateProductRequest,
    ErrorResponse,
    ImageResponse,
    ProductListParams,
    ProductListResponse,
    ProductResponse,
    UpdateProductRequest,
    VariantResponse,
)
from catalog.infrastructure.models import ProductModel

router = APIRouter(prefix="/api/v1/products", tags=["products"])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Not Found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    422: {"model": ErrorResponse, "description": "Validation Error"},
}


def _product_to_response(product: ProductModel) -> ProductResponse:
    """Map an ORM product (with loaded relations) to a response schema."""
    return ProductResponse(
        id=product.id,
        slug=product.slug,
        name=product.name,
        description=product.description,
        price=product.price,
        currency=product.currency,
        status=product.status,
        category_id=product.category_id,
        category_name=product.category.name if product.category else "",
        brand_id=product.brand_id,
        brand_name=product.brand.name if product.brand else None,
        cover_image=product.cover_image,
        images=[
            ImageResponse(id=img.id, url=img.url, sort_order=img.sort_order)
            for img in product.images
        ],
        variants=[
            VariantResponse.model_validate(v)
            for v in getattr(product, "variants", [])
        ],
        created_at=product.created_at,
        updated_at=product.updated_at,
        published_at=product.published_at,
    )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
    summary="Create a new product",
    description="Create a product. The slug is generated automatically from the name.",
)
async def create_product(
    data: CreateProductRequest,
    service: ProductServiceDep,
    admin: AdminPrincipal,
) -> ProductResponse:
    """Validate, persist, and return a new product."""
    product = await service.create_product(data)
    return _product_to_response(product)


@router.get(
    "",
    response_model=ProductListResponse,
    responses=ERROR_RESPONSES,
    summary="List products with filtering, sorting and pagination",
    description="Public listing returns only ACTIVE products by default.",
)
async def list_products(
    params: Annotated[ProductListParams, Query()],
    service: ProductServiceDep,
) -> ProductListResponse:
    """Execute a filtered, sorted, and paginated product search."""
    page = await service.search(params)
    return ProductListResponse(
        items=[_product_to_response(p) for p in page.items],
        total=page.total,
        limit=params.limit,
        offset=params.offset,
    )


@router.get(
    "/{slug}",
    response_model=ProductResponse,
    responses=ERROR_RESPONSES,
    summary="Get product by slug (public, ACTIVE only)",
    description="Returns 404 for HIDDEN or ARCHIVED products.",
)
async def get_product(
    slug: str,
    service: ProductServiceDep,
) -> ProductResponse:
    """Return an ACTIVE product by its slug or ID."""
    try:
        product_id = uuid.UUID(slug)
        product = await service.get_by_id(product_id)
    except ValueError:
        product = await service.get_by_slug(slug)
    return _product_to_response(product)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    responses=ERROR_RESPONSES,
    summary="Partially update a product",
    description="Only non-null fields are applied. The slug is never changed.",
)
async def update_product(
    product_id: uuid.UUID,
    data: UpdateProductRequest,
    service: ProductServiceDep,
    admin: AdminPrincipal,
) -> ProductResponse:
    """Apply a partial update to an existing product."""
    product = await service.update_product(product_id, data)
    return _product_to_response(product)


@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
    responses=ERROR_RESPONSES,
    summary="Archive a product (soft delete)",
    description="Sets the product status to ARCHIVED. The record is NOT deleted.",
)
async def archive_product(
    product_id: uuid.UUID,
    service: ProductServiceDep,
    admin: AdminPrincipal,
) -> ProductResponse:
    """Soft-delete a product by archiving it."""
    product = await service.archive_product(product_id)
    return _product_to_response(product)
