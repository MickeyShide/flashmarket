"""Admin API routes for drop management."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from drops.api.dependencies import DropServiceDep
from drops.application.schemas import (
    AddDropItemRequest,
    CreateDropRequest,
    DropItemResponse,
    DropListParams,
    DropListResponse,
    DropResponse,
    UpdateDropRequest,
)

router = APIRouter(prefix="/api/v1/admin/drops", tags=["admin-drops"])


@router.post(
    "/",
    response_model=DropResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new drop",
)
async def create_drop(
    data: CreateDropRequest,
    service: DropServiceDep,
) -> DropResponse:
    """Create a new drop campaign in DRAFT status."""
    drop = await service.create_drop(data)
    return DropResponse.model_validate(drop)


@router.get(
    "/",
    response_model=DropListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all drops (admin view)",
)
async def list_drops(
    params: Annotated[DropListParams, Query()],
    service: DropServiceDep,
) -> DropListResponse:
    """List drops across all statuses with pagination."""
    page = await service.list_all(params)
    items_response = [DropResponse.model_validate(drop) for drop in page.items]
    return DropListResponse(
        items=items_response,
        total=page.total,
        limit=params.limit,
        offset=params.offset,
    )


@router.get(
    "/{drop_id}",
    response_model=DropResponse,
    status_code=status.HTTP_200_OK,
    summary="Get drop by ID",
)
async def get_drop(
    drop_id: UUID,
    service: DropServiceDep,
) -> DropResponse:
    """Get full drop details by ID."""
    drop = await service.get_by_id(drop_id)
    return DropResponse.model_validate(drop)


@router.patch(
    "/{drop_id}",
    response_model=DropResponse,
    status_code=status.HTTP_200_OK,
    summary="Update drop",
)
async def update_drop(
    drop_id: UUID,
    data: UpdateDropRequest,
    service: DropServiceDep,
) -> DropResponse:
    """Update fields of a DRAFT or SCHEDULED drop."""
    drop = await service.update_drop(drop_id, data)
    return DropResponse.model_validate(drop)


@router.post(
    "/{drop_id}/schedule",
    response_model=DropResponse,
    status_code=status.HTTP_200_OK,
    summary="Schedule drop (DRAFT -> SCHEDULED)",
)
async def schedule_drop(
    drop_id: UUID,
    service: DropServiceDep,
) -> DropResponse:
    """Transition drop from DRAFT to SCHEDULED."""
    drop = await service.schedule_drop(drop_id)
    return DropResponse.model_validate(drop)


@router.post(
    "/{drop_id}/start",
    response_model=DropResponse,
    status_code=status.HTTP_200_OK,
    summary="Start drop (SCHEDULED -> ACTIVE)",
)
async def start_drop(
    drop_id: UUID,
    service: DropServiceDep,
) -> DropResponse:
    """Transition drop from SCHEDULED to ACTIVE."""
    drop = await service.start_drop(drop_id)
    return DropResponse.model_validate(drop)


@router.post(
    "/{drop_id}/end",
    response_model=DropResponse,
    status_code=status.HTTP_200_OK,
    summary="End drop (ACTIVE -> ENDED)",
)
async def end_drop(
    drop_id: UUID,
    service: DropServiceDep,
) -> DropResponse:
    """Transition drop from ACTIVE to ENDED."""
    drop = await service.end_drop(drop_id)
    return DropResponse.model_validate(drop)


@router.post(
    "/{drop_id}/cancel",
    response_model=DropResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel drop",
)
async def cancel_drop(
    drop_id: UUID,
    service: DropServiceDep,
) -> DropResponse:
    """Cancel drop from DRAFT, SCHEDULED, or ACTIVE status."""
    drop = await service.cancel_drop(drop_id)
    return DropResponse.model_validate(drop)


@router.post(
    "/{drop_id}/items",
    response_model=DropItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add item to drop",
)
async def add_item(
    drop_id: UUID,
    data: AddDropItemRequest,
    service: DropServiceDep,
) -> DropItemResponse:
    """Add a product item to a drop campaign."""
    item = await service.add_item(drop_id, data)
    return DropItemResponse.model_validate(item)


@router.delete(
    "/{drop_id}/items/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove item from drop",
)
async def remove_item(
    drop_id: UUID,
    product_id: UUID,
    service: DropServiceDep,
) -> None:
    """Remove a product item from a drop campaign."""
    await service.remove_item(drop_id, product_id)
