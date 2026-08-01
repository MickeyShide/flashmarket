"""API routes for promocodes management and validation."""

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from orders.api.dependencies import AdminPrincipal, CurrentPrincipal, PromocodeServiceDep
from orders.application.schemas import (
    CreatePromocodeRequest,
    PromocodeListParams,
    PromocodeListResponse,
    PromocodeResponse,
    PromocodeValidationResponse,
    UpdatePromocodeRequest,
    ValidatePromocodeRequest,
)
from orders.domain.exceptions import PromocodeError

router = APIRouter(prefix="/api/v1/promocodes", tags=["promocodes"])


@router.post(
    "/",
    response_model=PromocodeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new promocode (Admin)",
)
async def create_promocode(
    data: CreatePromocodeRequest,
    service: PromocodeServiceDep,
    admin: AdminPrincipal,
) -> PromocodeResponse:
    """Create a new promocode definition."""
    promo = await service.create_promocode(data)
    return PromocodeResponse.model_validate(promo)


@router.get(
    "/",
    response_model=PromocodeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List promocodes (Admin)",
)
async def list_promocodes(
    params: Annotated[PromocodeListParams, Query()],
    service: PromocodeServiceDep,
    admin: AdminPrincipal,
) -> PromocodeListResponse:
    """List all promocodes with pagination."""
    page = await service.list_promocodes(params.limit, params.offset)
    items_response = [PromocodeResponse.model_validate(p) for p in page.items]
    return PromocodeListResponse(
        items=items_response,
        total=page.total,
        limit=params.limit,
        offset=params.offset,
    )


@router.get(
    "/{promo_id}",
    response_model=PromocodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get promocode by ID (Admin)",
)
async def get_promocode(
    promo_id: UUID,
    service: PromocodeServiceDep,
    admin: AdminPrincipal,
) -> PromocodeResponse:
    """Get details of a specific promocode."""
    promo = await service.get_by_id(promo_id)
    return PromocodeResponse.model_validate(promo)


@router.patch(
    "/{promo_id}",
    response_model=PromocodeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update promocode (Admin)",
)
async def update_promocode(
    promo_id: UUID,
    data: UpdatePromocodeRequest,
    service: PromocodeServiceDep,
    admin: AdminPrincipal,
) -> PromocodeResponse:
    """Update fields of an existing promocode."""
    promo = await service.update_promocode(promo_id, data)
    return PromocodeResponse.model_validate(promo)


@router.post(
    "/validate",
    response_model=PromocodeValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate promocode (Authenticated user)",
)
async def validate_promocode(
    data: ValidatePromocodeRequest,
    service: PromocodeServiceDep,
    principal: CurrentPrincipal,
) -> PromocodeValidationResponse:
    """Validate whether a promocode is applicable to an order amount for a user."""
    if principal.role != "ADMIN" and data.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot validate promocode for another user",
        )
    try:
        res = await service.validate_and_apply(
            code=data.code,
            user_id=data.user_id,
            order_amount=data.order_amount,
            for_update=False,
        )
        return PromocodeValidationResponse(
            valid=True,
            discount_amount=res.discount_amount,
            final_amount=res.final_amount,
            error=None,
        )
    except PromocodeError as exc:
        return PromocodeValidationResponse(
            valid=False,
            discount_amount=Decimal("0"),
            final_amount=data.order_amount,
            error=exc.public_message,
        )
