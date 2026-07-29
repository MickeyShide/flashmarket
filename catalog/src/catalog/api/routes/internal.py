"""Internal product endpoints (any status, UUID lookup)."""

import uuid
from typing import Any

from fastapi import APIRouter

from catalog.api.dependencies import ProductServiceDep
from catalog.api.routes.products import _product_to_response
from catalog.application.schemas import ErrorResponse, ProductResponse

router = APIRouter(prefix="/api/v1/internal", tags=["internal"])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Not Found"},
}


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    responses=ERROR_RESPONSES,
    summary="Get product by ID (internal, any status)",
    description="Internal endpoint for other services. Returns product regardless of status.",
)
async def get_product_internal(
    product_id: uuid.UUID,
    service: ProductServiceDep,
) -> ProductResponse:
    """Return a product by primary key, including HIDDEN and ARCHIVED."""
    product = await service.get_by_id(product_id)
    return _product_to_response(product)
