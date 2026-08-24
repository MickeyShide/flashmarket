"""Async YooKassa API adapter."""

from __future__ import annotations

import asyncio
import logging
import random
import time
import uuid
from collections.abc import Awaitable, Callable
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from payments.application.contracts import ProviderPayment, ProviderRefund
from payments.domain.exceptions import (
    PaymentProviderAuthenticationFailed,
    PaymentProviderMalformedResponse,
    PaymentProviderRateLimited,
    PaymentProviderRejected,
    PaymentProviderResultUnknown,
    PaymentProviderUnavailable,
)
from payments.observability import (
    PROVIDER_CIRCUIT_OPEN,
    PROVIDER_DURATION,
    PROVIDER_IN_PROGRESS,
    PROVIDER_OPERATIONS,
)

logger = logging.getLogger(__name__)

Sleep = Callable[[float], Awaitable[None]]


class _CircuitBreaker:
    """Small process-local breaker that bounds repeated provider failures."""

    def __init__(self, *, failure_threshold: int, recovery_seconds: float) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_seconds = recovery_seconds
        self._failures = 0
        self._opened_at: float | None = None

    def ensure_request_allowed(self) -> None:
        if self._opened_at is None:
            return
        if time.monotonic() - self._opened_at >= self._recovery_seconds:
            self._opened_at = None
            self._failures = 0
            PROVIDER_CIRCUIT_OPEN.set(0)
            return
        raise PaymentProviderUnavailable

    def record_success(self) -> None:
        self._failures = 0
        self._opened_at = None
        PROVIDER_CIRCUIT_OPEN.set(0)

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._failure_threshold:
            self._opened_at = time.monotonic()
            PROVIDER_CIRCUIT_OPEN.set(1)


def kopecks_to_value(amount: int) -> str:
    """Convert integer kopecks to YooKassa's exact decimal string."""
    if amount <= 0:
        raise ValueError("amount must be positive")
    return f"{amount // 100}.{amount % 100:02d}"


def value_to_kopecks(value: object) -> int:
    """Convert a provider decimal amount to integer kopecks without float math."""
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PaymentProviderRejected("Payment provider returned an invalid amount") from exc
    kopecks = decimal_value * 100
    if kopecks != kopecks.to_integral_value():
        raise PaymentProviderRejected("Payment provider returned an invalid amount precision")
    return int(kopecks)


class YooKassaPaymentProvider:
    """Minimal adapter for hosted payments, status checks, and refunds."""

    def __init__(
        self,
        *,
        shop_id: str,
        secret_key: str,
        api_url: str,
        connect_timeout: float,
        read_timeout: float,
        max_connections: int = 20,
        max_keepalive_connections: int = 10,
        keepalive_expiry: float = 30.0,
        read_concurrency: int = 16,
        write_concurrency: int = 8,
        max_attempts: int = 2,
        retry_base_seconds: float = 0.25,
        retry_max_seconds: float = 2.0,
        circuit_failure_threshold: int = 5,
        circuit_recovery_seconds: float = 15.0,
        client: httpx.AsyncClient | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._shop_id = shop_id
        self._secret_key = secret_key
        self._api_url = api_url.rstrip("/") + "/"
        self._timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=read_timeout,
            pool=connect_timeout,
        )
        self._max_attempts = max_attempts
        self._retry_base_seconds = retry_base_seconds
        self._retry_max_seconds = retry_max_seconds
        self._sleep = sleep
        self._read_gate = asyncio.Semaphore(read_concurrency)
        self._write_gate = asyncio.Semaphore(write_concurrency)
        self._circuit = _CircuitBreaker(
            failure_threshold=circuit_failure_threshold,
            recovery_seconds=circuit_recovery_seconds,
        )
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self._api_url,
            auth=httpx.BasicAuth(self._shop_id, self._secret_key),
            timeout=self._timeout,
            limits=httpx.Limits(
                max_connections=max_connections,
                max_keepalive_connections=max_keepalive_connections,
                keepalive_expiry=keepalive_expiry,
            ),
            headers={"Accept": "application/json"},
        )

    async def aclose(self) -> None:
        """Close the process-lifetime HTTP pool when owned by this adapter."""
        if self._owns_client:
            await self._client.aclose()

    def _retry_delay(self, attempt: int, response: httpx.Response | None = None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                try:
                    return min(float(retry_after), self._retry_max_seconds)
                except ValueError:
                    pass
        ceiling = min(
            self._retry_base_seconds * (2**attempt),
            self._retry_max_seconds,
        )
        return random.uniform(ceiling / 2, ceiling)  # noqa: S311

    @staticmethod
    def _provider_error_id(response: httpx.Response) -> str | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        if isinstance(payload, dict) and isinstance(payload.get("id"), str):
            return str(payload["id"])
        return None

    @staticmethod
    def _temporary_exception(method: str) -> type[PaymentProviderUnavailable]:
        return PaymentProviderResultUnknown if method == "POST" else PaymentProviderUnavailable

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        operation = self._operation_name(method, path)
        headers: dict[str, str] = {}
        if idempotency_key is not None:
            headers["Idempotence-Key"] = idempotency_key

        gate_kind = "write" if method == "POST" else "read"
        gate = self._write_gate if method == "POST" else self._read_gate
        temporary_exception = self._temporary_exception(method)

        for attempt in range(self._max_attempts):
            self._circuit.ensure_request_allowed()
            response: httpx.Response | None = None
            started_at = time.perf_counter()
            in_progress = False
            try:
                async with gate:
                    PROVIDER_IN_PROGRESS.labels(kind=gate_kind).inc()
                    in_progress = True
                    response = await self._client.request(
                        method,
                        path.lstrip("/"),
                        json=json_body,
                        headers=headers,
                    )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                self._circuit.record_failure()
                if attempt + 1 < self._max_attempts:
                    await self._sleep(self._retry_delay(attempt))
                    continue
                PROVIDER_OPERATIONS.labels(operation=operation, result="transport_error").inc()
                raise temporary_exception from exc
            finally:
                PROVIDER_DURATION.labels(operation=operation).observe(
                    time.perf_counter() - started_at
                )
                if in_progress:
                    PROVIDER_IN_PROGRESS.labels(kind=gate_kind).dec()

            if response.status_code == 429:
                if attempt + 1 < self._max_attempts:
                    await self._sleep(self._retry_delay(attempt, response))
                    continue
                PROVIDER_OPERATIONS.labels(operation=operation, result="rate_limited").inc()
                raise PaymentProviderRateLimited
            if response.status_code >= 500:
                self._circuit.record_failure()
                if attempt + 1 < self._max_attempts:
                    await self._sleep(self._retry_delay(attempt, response))
                    continue
                PROVIDER_OPERATIONS.labels(operation=operation, result="server_error").inc()
                raise temporary_exception
            if response.status_code in {401, 403}:
                PROVIDER_OPERATIONS.labels(operation=operation, result="authentication_error").inc()
                raise PaymentProviderAuthenticationFailed
            if response.status_code >= 400:
                PROVIDER_OPERATIONS.labels(operation=operation, result="rejected").inc()
                provider_error_id = self._provider_error_id(response)
                logger.warning(
                    "Payment provider rejected an operation",
                    extra={
                        "operation": operation,
                        "provider_error_id": provider_error_id,
                        "provider_status_code": response.status_code,
                    },
                )
                raise PaymentProviderRejected(
                    f"Payment provider rejected the operation (HTTP {response.status_code})"
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise PaymentProviderMalformedResponse from exc
            if not isinstance(payload, dict):
                raise PaymentProviderMalformedResponse
            self._circuit.record_success()
            PROVIDER_OPERATIONS.labels(operation=operation, result="success").inc()
            return payload

        raise PaymentProviderUnavailable

    @staticmethod
    def _operation_name(method: str, path: str) -> str:
        resource = path.strip("/").split("/", 1)[0]
        action = "create" if method == "POST" else "get"
        return f"{action}_{resource}"

    @staticmethod
    def _payment(payload: dict[str, Any]) -> ProviderPayment:
        try:
            amount = payload["amount"]
            metadata = payload.get("metadata") or {}
            confirmation = payload.get("confirmation") or {}
            cancellation = payload.get("cancellation_details") or {}
            return ProviderPayment(
                id=str(payload["id"]),
                status=str(payload["status"]),
                amount=value_to_kopecks(amount["value"]),
                currency=str(amount["currency"]),
                test=bool(payload.get("test", False)),
                metadata={str(key): str(value) for key, value in metadata.items()},
                confirmation_url=(
                    str(confirmation["confirmation_url"])
                    if confirmation.get("confirmation_url")
                    else None
                ),
                cancellation_reason=(
                    str(cancellation["reason"]) if cancellation.get("reason") else None
                ),
            )
        except (KeyError, TypeError, AttributeError) as exc:
            raise PaymentProviderRejected(
                "Payment provider returned an invalid payment object"
            ) from exc

    @staticmethod
    def _refund(payload: dict[str, Any]) -> ProviderRefund:
        try:
            amount = payload["amount"]
            cancellation = payload.get("cancellation_details") or {}
            return ProviderRefund(
                id=str(payload["id"]),
                payment_id=str(payload["payment_id"]),
                status=str(payload["status"]),
                amount=value_to_kopecks(amount["value"]),
                currency=str(amount["currency"]),
                cancellation_reason=(
                    str(cancellation["reason"]) if cancellation.get("reason") else None
                ),
            )
        except (KeyError, TypeError, AttributeError) as exc:
            raise PaymentProviderRejected(
                "Payment provider returned an invalid refund object"
            ) from exc

    async def create_payment(
        self,
        *,
        payment_id: uuid.UUID,
        order_id: uuid.UUID,
        amount: int,
        currency: str,
        description: str,
        return_url: str,
        idempotency_key: str,
    ) -> ProviderPayment:
        payload = await self._request(
            "POST",
            "payments",
            idempotency_key=idempotency_key,
            json_body={
                "amount": {"value": kopecks_to_value(amount), "currency": currency},
                "capture": True,
                "confirmation": {"type": "redirect", "return_url": return_url},
                "description": description,
                "metadata": {"payment_id": str(payment_id), "order_id": str(order_id)},
            },
        )
        return self._payment(payload)

    async def get_payment(self, external_id: str) -> ProviderPayment:
        return self._payment(await self._request("GET", f"payments/{external_id}"))

    async def create_refund(
        self,
        *,
        payment: ProviderPayment,
        idempotency_key: str,
        reason: str,
    ) -> ProviderRefund:
        del reason
        payload = await self._request(
            "POST",
            "refunds",
            idempotency_key=idempotency_key,
            json_body={
                "payment_id": payment.id,
                "amount": {
                    "value": kopecks_to_value(payment.amount),
                    "currency": payment.currency,
                },
            },
        )
        return self._refund(payload)

    async def get_refund(self, external_id: str) -> ProviderRefund:
        return self._refund(await self._request("GET", f"refunds/{external_id}"))
