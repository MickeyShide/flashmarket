"""Payment API routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from payments.api.dependencies import AdminPrincipal, CurrentPrincipal, get_payment_service
from payments.application.schemas import (
    CheckoutResponse,
    CreatePaymentRequest,
    PaymentListParams,
    PaymentListResponse,
    PaymentResponse,
)
from payments.application.services.payment import PaymentService
from payments.domain.exceptions import PaymentProviderResultUnknown
from payments.infrastructure.models import PaymentModel

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


def _payment_response(payment: PaymentModel) -> PaymentResponse:
    return PaymentResponse.model_validate(payment)


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a payment for an order",
    openapi_extra={"x-flashmarket-access": "admin"},
)
async def create_payment(
    data: CreatePaymentRequest,
    admin: AdminPrincipal,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Create a pending payment for an administrative mock workflow."""
    del admin
    payment = await service.create_payment(data)
    return _payment_response(payment)


@router.post(
    "/orders/{order_id:uuid}/checkout",
    response_model=CheckoutResponse,
    responses={
        status.HTTP_202_ACCEPTED: {
            "model": CheckoutResponse,
            "description": "Provider result is being reconciled",
        }
    },
    summary="Start or resume hosted checkout",
    openapi_extra={"x-flashmarket-access": "authenticated"},
)
async def start_checkout(
    order_id: UUID,
    principal: CurrentPrincipal,
    service: PaymentService = Depends(get_payment_service),
) -> CheckoutResponse | JSONResponse:
    """Create a provider payment from the authoritative PaymentRequested event."""
    payment = await service.get_payment_by_order_id(order_id)
    if principal.role != "ADMIN" and payment.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot pay another user's order",
        )
    try:
        payment = await service.start_checkout(order_id)
    except PaymentProviderResultUnknown:
        response = CheckoutResponse(
            payment_id=payment.id,
            status=payment.status,
            preparation_status="pending",
            retry_after_seconds=2,
        )
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=response.model_dump(mode="json"),
            headers={"Retry-After": "2"},
        )
    if payment.confirmation_url is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider did not return a confirmation URL",
        )
    return CheckoutResponse(
        payment_id=payment.id,
        status=payment.status,
        confirmation_url=payment.confirmation_url,
    )


@router.get(
    "/orders/{order_id:uuid}",
    response_model=PaymentResponse,
    summary="Get payment by order",
    openapi_extra={"x-flashmarket-access": "authenticated"},
)
async def get_order_payment(
    order_id: UUID,
    principal: CurrentPrincipal,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Return the authoritative payment for an order."""
    payment = await service.get_payment_by_order_id(order_id)
    if principal.role != "ADMIN" and payment.user_id != principal.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view another user's payment",
        )
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
    openapi_extra={"x-flashmarket-access": "authenticated"},
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
    openapi_extra={"x-flashmarket-access": "admin"},
)
async def confirm_payment(
    payment_id: UUID,
    admin: AdminPrincipal,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Mark a pending payment as successful (admin/provider callback only)."""
    del admin
    payment = await service.confirm_payment(payment_id)
    return _payment_response(payment)


@router.post(
    "/{payment_id}/fail",
    response_model=PaymentResponse,
    summary="Fail payment",
    openapi_extra={"x-flashmarket-access": "admin"},
)
async def fail_payment(
    payment_id: UUID,
    admin: AdminPrincipal,
    service: PaymentService = Depends(get_payment_service),
) -> PaymentResponse:
    """Mark a pending payment as failed (admin/provider callback only)."""
    del admin
    payment = await service.fail_payment(payment_id)
    return _payment_response(payment)


@router.post(
    "/{payment_id}/cancel",
    response_model=PaymentResponse,
    summary="Cancel payment",
    openapi_extra={"x-flashmarket-access": "authenticated"},
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
