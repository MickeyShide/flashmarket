"""Public callbacks from payment providers."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from payments.api.dependencies import get_payment_service
from payments.application.services.payment import PaymentService
from payments.config import get_settings
from payments.observability import WEBHOOK_EVENTS

router = APIRouter(prefix="/api/v1/payments/webhooks", tags=["payment-webhooks"])


@router.post(
    "/yookassa",
    status_code=200,
    summary="Receive a YooKassa notification",
    openapi_extra={
        "x-flashmarket-access": "anonymous",
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["type", "event", "object"],
                        "properties": {
                            "type": {"type": "string"},
                            "event": {"type": "string"},
                            "object": {"type": "object", "additionalProperties": True},
                        },
                    }
                }
            },
        },
    },
)
async def yookassa_webhook(
    request: Request,
    service: PaymentService = Depends(get_payment_service),
) -> dict[str, str]:
    """Durably accept a bounded notification without provider network I/O."""
    settings = get_settings()
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if settings.yookassa_webhook_require_https and not (
        request.url.scheme == "https" or forwarded_proto == "https"
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="HTTPS required")
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > settings.webhook_max_body_bytes:
                raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST) from exc
    raw_body = await request.body()
    if len(raw_body) > settings.webhook_max_body_bytes:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE)
    source_ip = request.client.host if request.client is not None else None
    result = await service.ingest_webhook(raw_body, source_ip=source_ip)
    WEBHOOK_EVENTS.labels(event="notification", result=result).inc()
    return {"status": result}
