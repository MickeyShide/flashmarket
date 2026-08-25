"""Pure conversion tests for the YooKassa adapter."""

import uuid

import httpx
import pytest

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
