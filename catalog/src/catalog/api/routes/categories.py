"""Category API endpoints."""

from typing import Any

from fastapi import APIRouter, status

from catalog.api.dependencies import AdminPrincipal, CategoryServiceDep
from catalog.application.schemas import (
    CategoryResponse,
    CategoryTreeNode,
    CreateCategoryRequest,
    ErrorResponse,
)

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    404: {"model": ErrorResponse, "description": "Not Found"},
    409: {"model": ErrorResponse, "description": "Conflict"},
    422: {"model": ErrorResponse, "description": "Validation Error"},
}


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    responses=ERROR_RESPONSES,
    summary="Create a new category",
    description="Create a category. Nested categories are supported via parent_id.",
)
async def create_category(
    data: CreateCategoryRequest,
    service: CategoryServiceDep,
    admin: AdminPrincipal,
) -> CategoryResponse:
    """Persist a new category and return its representation."""
    category = await service.create_category(data)
    return CategoryResponse(
        id=category.id,
        name=category.name,
        slug=category.slug,
        parent_id=category.parent_id,
        created_at=category.created_at,
    )


@router.get(
    "",
    response_model=list[CategoryTreeNode],
    responses=ERROR_RESPONSES,
    summary="Get category tree",
    description="Return the full category hierarchy as a nested tree.",
)
async def list_categories(
    service: CategoryServiceDep,
) -> list[CategoryTreeNode]:
    """Build and return the category tree."""
    return await service.get_category_tree()
