"""Stock and reservation API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from inventory.api.dependencies import (
    AdminPrincipal,
    CurrentPrincipal,
    InventoryServiceDep,
)
from inventory.application.schemas import (
    CommitRequest,
    ReleaseRequest,
    ReservationResponse,
    ReservationResult,
    ReserveRequest,
    StockCreateRequest,
    StockResponse,
    StockUpdateRequest,
)
from inventory.infrastructure.models import ReservationModel, StockModel

router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])


def _stock_response(stock: StockModel) -> StockResponse:
    return StockResponse.model_validate(stock)


def _reservation_response(reservation: ReservationModel) -> ReservationResponse:
    return ReservationResponse.model_validate(reservation)


@router.post(
    "",
    response_model=StockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or reset stock for a product",
)
async def create_stock(
    data: StockCreateRequest,
    service: InventoryServiceDep,
    admin: AdminPrincipal,
) -> StockResponse:
    """Initialize stock for a product."""
    stock = await service.create_stock(data)
    return _stock_response(stock)


@router.get(
    "/{product_id}",
    response_model=StockResponse,
    summary="Get stock for a product",
)
async def get_stock(
    product_id: UUID,
    service: InventoryServiceDep,
    variant_id: UUID | None = None,
) -> StockResponse:
    """Return current stock counters for a product or variant."""
    stock = await service.get_stock(product_id, variant_id)
    return _stock_response(stock)


@router.patch(
    "/{product_id}",
    response_model=StockResponse,
    summary="Update total stock",
)
async def update_stock(
    product_id: UUID,
    data: StockUpdateRequest,
    service: InventoryServiceDep,
    admin: AdminPrincipal,
    variant_id: UUID | None = None,
) -> StockResponse:
    """Adjust the total stock of a product or variant."""
    stock = await service.update_total(product_id, data, variant_id)
    return _stock_response(stock)


@router.post(
    "/{product_id}/reserve",
    response_model=ReservationResult,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve stock",
)
async def reserve(
    product_id: UUID,
    data: ReserveRequest,
    service: InventoryServiceDep,
    principal: CurrentPrincipal,
) -> ReservationResult:
    """Reserve one or more units for a user."""
    if principal.role != "ADMIN" and data.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot reserve stock for another user",
        )
    reservation = await service.reserve(product_id, data)
    stock = await service.get_stock(product_id, data.variant_id)
    return ReservationResult(
        reservation=_reservation_response(reservation),
        stock=_stock_response(stock),
    )


@router.post(
    "/{product_id}/commit",
    response_model=ReservationResponse,
    summary="Commit a reservation to a sale",
)
async def commit(
    product_id: UUID,
    data: CommitRequest,
    service: InventoryServiceDep,
    admin: AdminPrincipal,
) -> ReservationResponse:
    """Convert an active reservation into a confirmed sale."""
    reservation = await service.commit(product_id, data)
    return _reservation_response(reservation)


@router.post(
    "/{product_id}/release",
    response_model=ReservationResponse,
    summary="Release a reservation",
)
async def release(
    product_id: UUID,
    data: ReleaseRequest,
    service: InventoryServiceDep,
    principal: CurrentPrincipal,
) -> ReservationResponse:
    """Manually release an active reservation."""
    if principal.role != "ADMIN":
        res = await service._reservation_repo.get_by_order_id(data.order_id)
        if res is not None and res.user_id != principal.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot release reservation belonging to another user",
            )
    reservation = await service.release(product_id, data)
    return _reservation_response(reservation)
