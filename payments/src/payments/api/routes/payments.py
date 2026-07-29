"""Payment API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from payments.api.dependencies import get_payment_service
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
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Create a pending payment for an order."""
    payment = await service.create_payment(data)
    return _payment_response(payment)


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    summary="Get a payment",
)
async def get_payment(
    payment_id: UUID,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Return a single payment by id."""
    payment = await service.get_payment(payment_id)
    return _payment_response(payment)


@router.get(
    "/users/{user_id}",
    response_model=PaymentListResponse,
    summary="List user payments",
)
async def list_payments(
    user_id: UUID,
    params: PaymentListParams = Depends(),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentListResponse:
    """Return paginated payments for a user."""
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
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Mark a pending payment as successful."""
    payment = await service.confirm_payment(payment_id)
    return _payment_response(payment)


@router.post(
    "/{payment_id}/fail",
    response_model=PaymentResponse,
    summary="Fail payment",
)
async def fail_payment(
    payment_id: UUID,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Mark a pending payment as failed."""
    payment = await service.fail_payment(payment_id)
    return _payment_response(payment)


@router.post(
    "/{payment_id}/cancel",
    response_model=PaymentResponse,
    summary="Cancel payment",
)
async def cancel_payment(
    payment_id: UUID,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Cancel a pending payment."""
    payment = await service.cancel_payment(payment_id)
    return _payment_response(payment)
