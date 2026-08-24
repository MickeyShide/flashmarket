"""Async YooKassa API adapter."""

from __future__ import annotations

import asyncio
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from payments.application.contracts import ProviderPayment, ProviderRefund
from payments.domain.exceptions import PaymentProviderRejected, PaymentProviderUnavailable
from payments.observability import PROVIDER_OPERATIONS


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

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, object] | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        operation = self._operation_name(method, path)
        headers = {"Accept": "application/json"}
        if idempotency_key is not None:
            headers["Idempotence-Key"] = idempotency_key

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    base_url=self._api_url,
                    auth=httpx.BasicAuth(self._shop_id, self._secret_key),
                    timeout=self._timeout,
                ) as client:
                    response = await client.request(
                        method,
                        path.lstrip("/"),
                        json=json_body,
                        headers=headers,
                    )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt == 0:
                    await asyncio.sleep(0)
                    continue
                PROVIDER_OPERATIONS.labels(operation=operation, result="transport_error").inc()
                raise PaymentProviderUnavailable from exc

            if response.status_code >= 500:
                if attempt == 0:
                    await asyncio.sleep(0)
                    continue
                PROVIDER_OPERATIONS.labels(operation=operation, result="server_error").inc()
                raise PaymentProviderUnavailable
            if response.status_code >= 400:
                PROVIDER_OPERATIONS.labels(operation=operation, result="rejected").inc()
                raise PaymentProviderRejected(
                    f"Payment provider rejected the operation (HTTP {response.status_code})"
                )
            try:
                payload = response.json()
            except ValueError as exc:
                raise PaymentProviderRejected(
                    "Payment provider returned an invalid response"
                ) from exc
            if not isinstance(payload, dict):
                raise PaymentProviderRejected("Payment provider returned an invalid response")
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
