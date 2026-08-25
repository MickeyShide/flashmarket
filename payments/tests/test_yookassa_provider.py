"""Pure conversion tests for the YooKassa adapter."""

import json
import uuid
from decimal import Decimal

import httpx
import pytest

from payments.application.contracts import (
    ProviderPayment,
    ProviderReceipt,
    ProviderReceiptCustomer,
    ProviderReceiptItem,
)
from payments.domain.exceptions import (
    PaymentProviderMalformedResponse,
    PaymentProviderRateLimited,
    PaymentProviderRejected,
    PaymentProviderResultUnknown,
    PaymentProviderUnavailable,
)
from payments.infrastructure.providers.yookassa import (
    YooKassaPaymentProvider,
    kopecks_to_value,
    value_to_kopecks,
)


def test_money_conversion_uses_exact_decimal_values() -> None:
    assert kopecks_to_value(1) == "0.01"
    assert kopecks_to_value(12_990) == "129.90"
    assert value_to_kopecks("129.90") == 12_990


def test_provider_amount_rejects_fractional_kopecks() -> None:
    with pytest.raises(PaymentProviderRejected):
        value_to_kopecks("1.001")


def _provider(
    handler: httpx.AsyncBaseTransport,
    *,
    sleep: object | None = None,
    max_attempts: int = 2,
    circuit_failure_threshold: int = 5,
) -> tuple[YooKassaPaymentProvider, httpx.AsyncClient]:
    client = httpx.AsyncClient(
        base_url="https://api.yookassa.test/v3/",
        transport=handler,
    )
    kwargs: dict[str, object] = {}
    if sleep is not None:
        kwargs["sleep"] = sleep
    provider = YooKassaPaymentProvider(
        shop_id="shop",
        secret_key="secret",
        api_url="https://api.yookassa.test/v3",
        connect_timeout=1,
        read_timeout=1,
        max_attempts=max_attempts,
        retry_base_seconds=0.01,
        retry_max_seconds=0.02,
        circuit_failure_threshold=circuit_failure_threshold,
        client=client,
        **kwargs,  # type: ignore[arg-type]
    )
    return provider, client


def _payment_payload() -> dict[str, object]:
    return {
        "id": "payment-1",
        "status": "pending",
        "amount": {"value": "1.00", "currency": "RUB"},
        "test": True,
        "metadata": {"payment_id": str(uuid.UUID(int=1)), "order_id": str(uuid.UUID(int=2))},
        "confirmation": {"confirmation_url": "https://pay.test/confirm"},
        "expires_at": "2026-08-25T15:30:00Z",
    }


def _receipt(*, amount: int = 100) -> ProviderReceipt:
    return ProviderReceipt(
        customer=ProviderReceiptCustomer(email="buyer@example.test"),
        currency="RUB",
        items=(
            ProviderReceiptItem(
                description="Test product",
                quantity=Decimal("1"),
                amount=amount,
                vat_code=1,
                payment_subject="commodity",
                payment_mode="full_payment",
                measure="piece",
            ),
        ),
    )


@pytest.mark.asyncio
async def test_provider_serializes_payment_and_refund_receipts_exactly() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/payments"):
            return httpx.Response(200, json=_payment_payload())
        return httpx.Response(
            200,
            json={
                "id": "refund-1",
                "payment_id": "payment-1",
                "status": "pending",
                "amount": {"value": "0.50", "currency": "RUB"},
            },
        )

    provider, client = _provider(httpx.MockTransport(handler))
    payment = await provider.create_payment(
        payment_id=uuid.UUID(int=1),
        attempt_id=uuid.UUID(int=3),
        order_id=uuid.UUID(int=2),
        amount=100,
        currency="RUB",
        description="Order",
        return_url="https://shop.test/payment/return",
        idempotency_key="operation-payment",
        receipt=_receipt(),
    )
    await provider.create_refund(
        payment=ProviderPayment(
            id=payment.id,
            status="succeeded",
            amount=100,
            currency="RUB",
            test=True,
            metadata=payment.metadata,
        ),
        amount=50,
        idempotency_key="operation-refund",
        reason="partial",
        receipt=_receipt(amount=50),
    )

    payment_json = json.loads(requests[0].content)
    refund_json = json.loads(requests[1].content)
    assert payment_json["receipt"] == {
        "customer": {"email": "buyer@example.test"},
        "items": [
            {
                "description": "Test product",
                "quantity": "1",
                "amount": {"value": "1.00", "currency": "RUB"},
                "vat_code": 1,
                "payment_subject": "commodity",
                "payment_mode": "full_payment",
                "measure": "piece",
            }
        ],
    }
    assert refund_json["receipt"]["items"][0]["amount"]["value"] == "0.50"
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_logs_bounded_yookassa_error_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    description = "Receipt is missing or illegal\n" + ("x" * 700)
    provider, client = _provider(
        httpx.MockTransport(
            lambda _request: httpx.Response(
                400,
                json={
                    "type": "error",
                    "id": "provider-error-id",
                    "code": "invalid_request",
                    "parameter": "receipt",
                    "description": description,
                },
            )
        )
    )

    with caplog.at_level("WARNING"), pytest.raises(PaymentProviderRejected):
        await provider.create_payment(
            payment_id=uuid.UUID(int=1),
            attempt_id=uuid.UUID(int=3),
            order_id=uuid.UUID(int=2),
            amount=100,
            currency="RUB",
            description="Order",
            return_url="https://shop.test/payment/return",
            idempotency_key="operation-rejected",
            receipt=_receipt(),
        )

    record = next(record for record in caplog.records if record.name.endswith("yookassa"))
    assert record.provider_error_id == "provider-error-id"  # type: ignore[attr-defined]
    assert record.provider_error_code == "invalid_request"  # type: ignore[attr-defined]
    assert record.provider_error_parameter == "receipt"  # type: ignore[attr-defined]
    logged_description = record.provider_error_description  # type: ignore[attr-defined]
    assert "\n" not in logged_description
    assert len(logged_description) == 512
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_retries_server_error_with_nonzero_backoff() -> None:
    calls = 0
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(500, json={"type": "error"})
        return httpx.Response(200, json=_payment_payload())

    provider, client = _provider(httpx.MockTransport(handler), sleep=sleep)
    payment = await provider.get_payment("payment-1")

    assert payment.id == "payment-1"
    assert payment.expires_at is not None
    assert payment.expires_at.isoformat() == "2026-08-25T15:30:00+00:00"
    assert calls == 2
    assert len(delays) == 1
    assert delays[0] > 0
    assert not client.is_closed
    await client.aclose()


@pytest.mark.asyncio
async def test_provider_classifies_malformed_successful_write_as_uncertain() -> None:
    provider, client = _provider(
        httpx.MockTransport(lambda _request: httpx.Response(200, json={"status": "pending"}))
    )

    with pytest.raises(PaymentProviderMalformedResponse):
        await provider.create_payment(
            payment_id=uuid.UUID(int=1),
            attempt_id=uuid.UUID(int=3),
            order_id=uuid.UUID(int=2),
            amount=100,
            currency="RUB",
            description="Order",
            return_url="https://shop.test/payment/return",
            idempotency_key="operation-malformed",
        )

    await client.aclose()


@pytest.mark.asyncio
async def test_provider_classifies_exhausted_rate_limit() -> None:
    async def sleep(_delay: float) -> None:
        return None

    transport = httpx.MockTransport(
        lambda _request: httpx.Response(429, headers={"Retry-After": "0.01"})
    )
    provider, client = _provider(transport, sleep=sleep)

    with pytest.raises(PaymentProviderRateLimited):
        await provider.get_payment("payment-1")

    await client.aclose()


@pytest.mark.asyncio
async def test_provider_classifies_uncertain_financial_write() -> None:
    async def sleep(_delay: float) -> None:
        return None

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("lost response", request=request)

    provider, client = _provider(httpx.MockTransport(handler), sleep=sleep)

    with pytest.raises(PaymentProviderResultUnknown):
        await provider.create_payment(
            payment_id=uuid.UUID(int=1),
            attempt_id=uuid.UUID(int=3),
            order_id=uuid.UUID(int=2),
            amount=100,
            currency="RUB",
            description="Order",
            return_url="https://shop.test/payment/return",
            idempotency_key="operation-1",
        )

    await client.aclose()


@pytest.mark.asyncio
async def test_provider_circuit_opens_after_repeated_failures() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("offline", request=request)

    provider, client = _provider(
        httpx.MockTransport(handler),
        max_attempts=1,
        circuit_failure_threshold=2,
    )

    with pytest.raises(PaymentProviderUnavailable):
        await provider.get_payment("payment-1")
    with pytest.raises(PaymentProviderUnavailable):
        await provider.get_payment("payment-1")
    with pytest.raises(PaymentProviderUnavailable):
        await provider.get_payment("payment-1")

    assert calls == 2
    await client.aclose()
