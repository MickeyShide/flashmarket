"""Order API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from orders.api.dependencies import AdminPrincipal, CurrentPrincipal, get_order_service
from orders.application.schemas import (
    CreateOrderBatchRequest,
    CreateOrderRequest,
    OrderBatchResponse,
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


@router.post(
    "/batch",
    response_model=OrderBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a checkout from reserved lines",
)
async def create_order_batch(
    data: CreateOrderBatchRequest,
    principal: CurrentPrincipal,
    service: OrderService = Depends(get_order_service),
) -> OrderBatchResponse:
    user_id = data.lines[0].user_id
    if principal.role != "ADMIN" and user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create checkout for another user",
        )
    result = await service.create_batch(data)
    return OrderBatchResponse(
        checkout_id=result.checkout_id,
        orders=[_order_response(order) for order in result.orders],
        original_amount=result.original_amount,
        discount_amount=result.discount_amount,
        final_amount=result.final_amount,
    )


@router.get(
    "/{order_id:uuid}",
    response_model=OrderResponse,
    summary="Get an order",
    openapi_extra={"x-flashmarket-access": "authenticated"},
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
    admin: AdminPrincipal,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Confirm an order after a successful payment (admin/internal only)."""
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
    admin: AdminPrincipal,
    service: OrderService = Depends(get_order_service),
) -> OrderResponse:
    """Mark an order as cancelled after a failed payment (admin/internal only)."""
    order = await service.fail_payment(order_id, payment_id)
    return _order_response(order)
