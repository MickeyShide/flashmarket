"""Public callbacks from payment providers."""

from fastapi import APIRouter, Depends

from payments.api.dependencies import get_payment_service
from payments.application.schemas import YooKassaWebhook
from payments.application.services.payment import PaymentService
from payments.domain.exceptions import PaymentVerificationFailed
from payments.observability import WEBHOOK_EVENTS

router = APIRouter(prefix="/api/v1/payments/webhooks", tags=["payment-webhooks"])


@router.post("/yookassa", status_code=200, summary="Receive a YooKassa notification")
async def yookassa_webhook(
    notification: YooKassaWebhook,
    service: PaymentService = Depends(get_payment_service),
) -> dict[str, str]:
    """Treat the notification as a hint and verify current state through YooKassa API."""
    if notification.type != "notification":
        raise PaymentVerificationFailed("Invalid notification type")
    external_id = notification.object.get("id")
    if not isinstance(external_id, str) or not external_id:
        raise PaymentVerificationFailed("Notification object identifier is missing")

    if notification.event in {"payment.succeeded", "payment.canceled"}:
        await service.reconcile_external_payment(external_id)
    elif notification.event == "refund.succeeded":
        await service.reconcile_refund(external_id)
    else:
        WEBHOOK_EVENTS.labels(event=notification.event, result="ignored").inc()
        return {"status": "ignored"}
    WEBHOOK_EVENTS.labels(event=notification.event, result="processed").inc()
    return {"status": "ok"}
