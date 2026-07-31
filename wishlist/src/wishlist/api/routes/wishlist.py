"""Wishlist API routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from wishlist.api.dependencies import WishlistServiceDep
from wishlist.application.schemas import (
    AddToWishlistRequest,
    CheckWishlistRequest,
    WishlistCheckResponse,
    WishlistItemResponse,
    WishlistListParams,
    WishlistListResponse,
)

router = APIRouter(prefix="/api/v1/wishlist", tags=["wishlist"])


@router.post(
    "/users/{user_id}/items",
    response_model=WishlistItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add product to user wishlist",
)
async def add_item(
    user_id: UUID,
    data: AddToWishlistRequest,
    service: WishlistServiceDep,
) -> WishlistItemResponse:
    """Add a product to user's wishlist."""
    item = await service.add_item(user_id, data)
    return WishlistItemResponse.model_validate(item)


@router.delete(
    "/users/{user_id}/items/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove product from user wishlist",
)
async def remove_item(
    user_id: UUID,
    product_id: UUID,
    service: WishlistServiceDep,
) -> None:
    """Remove a product from user's wishlist."""
    await service.remove_item(user_id, product_id)


@router.get(
    "/users/{user_id}/items",
    response_model=WishlistListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user wishlist items",
)
async def list_items(
    user_id: UUID,
    params: Annotated[WishlistListParams, Query()],
    service: WishlistServiceDep,
) -> WishlistListResponse:
    """List wishlist items for user with pagination."""
    page = await service.list_items(user_id, params)
    items_response = [WishlistItemResponse.model_validate(item) for item in page.items]
    return WishlistListResponse(
        items=items_response,
        total=page.total,
        limit=params.limit,
        offset=params.offset,
    )


@router.post(
    "/users/{user_id}/check",
    response_model=WishlistCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check if products are in user wishlist",
)
async def check_items(
    user_id: UUID,
    data: CheckWishlistRequest,
    service: WishlistServiceDep,
) -> WishlistCheckResponse:
    """Batch check which of given product IDs are in user's wishlist."""
    found_ids = await service.check_items(user_id, data.product_ids)
    return WishlistCheckResponse(product_ids=list(found_ids))
