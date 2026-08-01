"""Payment API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from payments.api.dependencies import CurrentPrincipal, get_payment_service
from payments.application.schemas import (
    CreatePaymentRequest,
    PaymentListParams,
    PaymentListResponse,
    PaymentResponse,
)
from payments.application.services.payment import PaymentService
from payments.infrastructure.models import PaymentModel

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


def _payment_response(payment: PaymentModel) -> PaymentResponse:
    return PaymentResponse.model_validate(payment)


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a payment for an order",
)
async def create_payment(
    data: CreatePaymentRequest,
    principal: CurrentPrincipal,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Create a pending payment for an order."""
    if principal.role != "ADMIN" and data.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create payment for another user",
        )
    payment = await service.create_payment(data)
    return _payment_response(payment)


@router.get(
    "/{payment_id:uuid}",
    response_model=PaymentResponse,
    summary="Get a payment",
    openapi_extra={"x-flashmarket-access": "authenticated"},
)
async def get_payment(
    payment_id: UUID,
    principal: CurrentPrincipal,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Return a single payment by id."""
    payment = await service.get_payment(payment_id)
    if principal.role != "ADMIN" and payment.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view another user's payment",
        )
    return _payment_response(payment)


@router.get(
    "/users/{user_id}",
    response_model=PaymentListResponse,
    summary="List user payments",
)
async def list_payments(
    user_id: UUID,
    principal: CurrentPrincipal,
    params: PaymentListParams = Depends(),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentListResponse:
    """Return paginated payments for a user."""
    if principal.role != "ADMIN" and user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot list another user's payments",
        )
    items, total = await service.list_user_payments(
        user_id,
        limit=params.limit,
        offset=params.offset,
    )
    return PaymentListResponse(
        items=[_payment_response(item) for item in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


@router.post(
    "/{payment_id}/confirm",
    response_model=PaymentResponse,
    summary="Confirm payment succeeded",
)
async def confirm_payment(
    payment_id: UUID,
    principal: CurrentPrincipal,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Mark a pending payment as successful."""
    p = await service.get_payment(payment_id)
    if principal.role != "ADMIN" and p.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot confirm another user's payment",
        )
    payment = await service.confirm_payment(payment_id)
    return _payment_response(payment)


@router.post(
    "/{payment_id}/fail",
    response_model=PaymentResponse,
    summary="Fail payment",
)
async def fail_payment(
    payment_id: UUID,
    principal: CurrentPrincipal,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Mark a pending payment as failed."""
    p = await service.get_payment(payment_id)
    if principal.role != "ADMIN" and p.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot fail another user's payment",
        )
    payment = await service.fail_payment(payment_id)
    return _payment_response(payment)


@router.post(
    "/{payment_id}/cancel",
    response_model=PaymentResponse,
    summary="Cancel payment",
)
async def cancel_payment(
    payment_id: UUID,
    principal: CurrentPrincipal,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Cancel a pending payment."""
    p = await service.get_payment(payment_id)
    if principal.role != "ADMIN" and p.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot cancel another user's payment",
        )
    payment = await service.cancel_payment(payment_id)
    return _payment_response(payment)
