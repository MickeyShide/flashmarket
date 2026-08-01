"""Order API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from orders.api.dependencies import CurrentPrincipal, get_order_service
from orders.application.schemas import (
    CreateOrderRequest,
    OrderListParams,
    OrderListResponse,
    OrderResponse,
)
from orders.application.services.order import OrderService
from orders.infrastructure.models import OrderModel

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


def _order_response(order: OrderModel) -> OrderResponse:
    return OrderResponse.model_validate(order)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an order from a reservation",
)
async def create_order(
    data: CreateOrderRequest,
    principal: CurrentPrincipal,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Create an order after stock has been reserved."""
    if principal.role != "ADMIN" and data.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create order for another user",
        )
    order = await service.create_order(data)
    return _order_response(order)


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    summary="Get an order",
)
async def get_order(
    order_id: UUID,
    principal: CurrentPrincipal,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Return a single order by id."""
    order = await service.get_by_id(order_id)
    if principal.role != "ADMIN" and order.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view another user's order",
        )
    return _order_response(order)


@router.get(
    "/users/{user_id}",
    response_model=OrderListResponse,
    summary="List user orders",
)
async def list_orders(
    user_id: UUID,
    principal: CurrentPrincipal,
    params: OrderListParams = Depends(),
    service: OrderService = Depends(get_order_service),
) -> OrderListResponse:
    """Return paginated orders for a user."""
    if principal.role != "ADMIN" and user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot list another user's orders",
        )
    items, total = await service.list_user_orders(
        user_id,
        limit=params.limit,
        offset=params.offset,
    )
    return OrderListResponse(
        items=[_order_response(item) for item in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


@router.post(
    "/{order_id}/confirm",
    response_model=OrderResponse,
    summary="Confirm order after payment",
)
async def confirm_order(
    order_id: UUID,
    payment_id: UUID,
    principal: CurrentPrincipal,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Confirm an order after a successful payment."""
    order_obj = await service.get_by_id(order_id)
    if principal.role != "ADMIN" and order_obj.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot confirm another user's order",
        )
    order = await service.confirm_payment(order_id, payment_id)
    return _order_response(order)


@router.post(
    "/{order_id}/fail",
    response_model=OrderResponse,
    summary="Fail order payment",
)
async def fail_order(
    order_id: UUID,
    payment_id: UUID,
    principal: CurrentPrincipal,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Mark an order as cancelled after a failed payment."""
    order_obj = await service.get_by_id(order_id)
    if principal.role != "ADMIN" and order_obj.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot fail another user's order",
        )
    order = await service.fail_payment(order_id, payment_id)
    return _order_response(order)
