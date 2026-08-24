"""Payment application service."""

from __future__ import annotations

import json
import uuid
from datetime import UTC

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.contracts import PaymentProvider, ProviderPayment, ProviderRefund
from payments.application.schemas import CreatePaymentRequest
from payments.domain.entities import PaymentEventType, PaymentStatus
from payments.domain.exceptions import (
    InvalidPaymentState,
    PaymentNotFound,
    PaymentNotReady,
    PaymentProviderRejected,
    PaymentVerificationFailed,
)
from payments.infrastructure.database import utc_now
from payments.infrastructure.models import PaymentModel
from payments.infrastructure.repositories.payment import OutboxRepository, PaymentRepository


class PaymentService:
    """Orchestrate the local lifecycle and the configured payment provider."""

    def __init__(
        self,
        session: AsyncSession,
        payment_repo: PaymentRepository,
        outbox_repo: OutboxRepository,
        provider: PaymentProvider | None = None,
        *,
        provider_name: str = "mock",
        return_url: str = "http://localhost/payment/return",
        test_mode_required: bool = True,
    ) -> None:
        self._session = session
        self._payment_repo = payment_repo
        self._outbox_repo = outbox_repo
        if provider is None:
            from payments.infrastructure.providers.mock import MockPaymentProvider

            provider = MockPaymentProvider()
        self._provider = provider
        self._provider_name = provider_name
        self._return_url = return_url
        self._test_mode_required = test_mode_required

    async def create_payment(self, data: CreatePaymentRequest) -> PaymentModel:
        """Create a pending payment for administrative/mock workflows."""
        existing = await self._payment_repo.get_by_order_id(data.order_id)
        if existing is not None:
            return existing

        payment = PaymentModel(
            order_id=data.order_id,
            user_id=data.user_id,
            amount=data.amount,
            currency=data.currency,
            provider=data.provider,
            status=PaymentStatus.PENDING,
            expires_at=data.expires_at,
        )
        try:
            await self._payment_repo.create(payment)
            await self._session.commit()
            await self._session.refresh(payment)
            return payment
        except IntegrityError:
            await self._session.rollback()
            existing = await self._payment_repo.get_by_order_id(data.order_id)
            if existing is not None:
                return existing
            raise

    @staticmethod
    def _ensure_not_expired(payment: PaymentModel) -> None:
        expires_at = payment.expires_at
        if expires_at is None:
            return
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if utc_now() >= expires_at:
            raise InvalidPaymentState("Payment deadline has expired")

    def _verify_provider_payment(
        self,
        local: PaymentModel,
        remote: ProviderPayment,
        *,
        require_confirmation: bool = False,
    ) -> None:
        if self._test_mode_required and not remote.test:
            raise PaymentVerificationFailed("Only YooKassa test payments are allowed")
        if remote.amount != local.amount or remote.currency != local.currency:
            raise PaymentVerificationFailed("Payment amount or currency does not match")
        if remote.metadata.get("payment_id") != str(local.id):
            raise PaymentVerificationFailed("Payment metadata does not match")
        if remote.metadata.get("order_id") != str(local.order_id):
            raise PaymentVerificationFailed("Order metadata does not match")
        if local.external_id is not None and local.external_id != remote.id:
            raise PaymentVerificationFailed("Provider payment identifier does not match")
        if require_confirmation and not remote.confirmation_url:
            raise PaymentProviderRejected("Payment provider did not return a confirmation URL")

    async def start_checkout(self, order_id: uuid.UUID) -> PaymentModel:
        """Create or reuse a hosted provider payment for an authoritative order payment."""
        payment = await self._payment_repo.get_by_order_id(order_id)
        if payment is None:
            raise PaymentNotReady
        if payment.status != PaymentStatus.PENDING:
            raise InvalidPaymentState(f"Cannot pay an order in status {payment.status}")
        if payment.provider != self._provider_name:
            raise InvalidPaymentState("Payment provider configuration changed")
        self._ensure_not_expired(payment)
        if payment.confirmation_url:
            return payment

        remote = await self._provider.create_payment(
            payment_id=payment.id,
            order_id=payment.order_id,
            amount=payment.amount,
            currency=payment.currency,
            description=f"FlashMarket order {payment.order_id}",
            return_url=(
                f"{self._return_url}{'&' if '?' in self._return_url else '?'}"
                f"order_id={payment.order_id}"
            ),
            idempotency_key=str(payment.id),
        )
        self._verify_provider_payment(payment, remote, require_confirmation=True)

        locked = await self._payment_repo.get_by_id_for_update(payment.id)
        if locked is None:
            raise PaymentNotFound
        if locked.confirmation_url:
            return locked
        self._verify_provider_payment(locked, remote, require_confirmation=True)
        locked.external_id = remote.id
        locked.external_status = remote.status
        locked.confirmation_url = remote.confirmation_url
        locked.provider_test = remote.test
        locked.cancellation_reason = remote.cancellation_reason
        await self._payment_repo.update(locked)
        await self._session.commit()
        await self._session.refresh(locked)
        return locked

    async def _emit_succeeded(self, payment: PaymentModel) -> None:
        payload = {
            "payment_id": str(payment.id),
            "order_id": str(payment.order_id),
            "user_id": str(payment.user_id),
            "amount": payment.amount,
            "currency": payment.currency,
            "external_id": payment.external_id,
        }
        await self._outbox_repo.add(
            PaymentEventType.PAYMENT_SUCCEEDED,
            json.dumps(payload, separators=(",", ":")),
        )

    async def _emit_failed(self, payment: PaymentModel, reason: str) -> None:
        payload = {
            "payment_id": str(payment.id),
            "order_id": str(payment.order_id),
            "user_id": str(payment.user_id),
            "amount": payment.amount,
            "currency": payment.currency,
            "reason": reason,
        }
        await self._outbox_repo.add(
            PaymentEventType.PAYMENT_FAILED,
            json.dumps(payload, separators=(",", ":")),
        )

    async def reconcile_payment(self, remote: ProviderPayment) -> PaymentModel:
        """Apply a provider's current status after full server-side verification."""
        local_id_raw = remote.metadata.get("payment_id")
        try:
            local_id = uuid.UUID(local_id_raw or "")
        except ValueError as exc:
            raise PaymentVerificationFailed("Payment metadata is missing") from exc

        payment = await self._payment_repo.get_by_id_for_update(local_id)
        if payment is None:
            raise PaymentVerificationFailed("Local payment was not found")
        self._verify_provider_payment(payment, remote)

        payment.external_id = remote.id
        payment.external_status = remote.status
        payment.provider_test = remote.test
        payment.cancellation_reason = remote.cancellation_reason

        if remote.status == "succeeded":
            if payment.status not in (PaymentStatus.SUCCESS, PaymentStatus.REFUNDED):
                payment.status = PaymentStatus.SUCCESS
                await self._emit_succeeded(payment)
        elif remote.status == "canceled":
            if payment.status == PaymentStatus.PENDING:
                payment.status = PaymentStatus.FAILED
                await self._emit_failed(
                    payment,
                    remote.cancellation_reason or "provider_cancelled",
                )

        await self._payment_repo.update(payment)
        await self._session.commit()
        await self._session.refresh(payment)
        return payment

    async def reconcile_external_payment(self, external_id: str) -> PaymentModel:
        """Fetch a provider payment and apply its verified current status."""
        remote = await self._provider.get_payment(external_id)
        if remote.id != external_id:
            raise PaymentVerificationFailed("Provider payment identifier does not match")
        return await self.reconcile_payment(remote)

    @staticmethod
    def _verify_refund(payment: PaymentModel, refund: ProviderRefund) -> None:
        if payment.external_id != refund.payment_id:
            raise PaymentVerificationFailed("Refund payment identifier does not match")
        if payment.amount != refund.amount or payment.currency != refund.currency:
            raise PaymentVerificationFailed("Refund amount or currency does not match")

    async def _finish_refund(
        self,
        payment: PaymentModel,
        refund: ProviderRefund,
        *,
        reason: str,
    ) -> None:
        payment.refund_external_id = refund.id
        payment.refund_status = refund.status
        if refund.status != "succeeded" or payment.status == PaymentStatus.REFUNDED:
            return
        payment.status = PaymentStatus.REFUNDED
        payload = {
            "payment_id": str(payment.id),
            "order_id": str(payment.order_id),
            "user_id": str(payment.user_id),
            "amount": payment.amount,
            "currency": payment.currency,
            "reason": reason,
        }
        await self._outbox_repo.add(
            PaymentEventType.PAYMENT_REFUNDED,
            json.dumps(payload, separators=(",", ":")),
        )

    async def _remote_for_refund(self, payment: PaymentModel) -> ProviderPayment:
        if payment.external_id is None:
            raise InvalidPaymentState("Payment has no provider identifier")
        if self._provider_name == "mock":
            return ProviderPayment(
                id=payment.external_id,
                status="succeeded",
                amount=payment.amount,
                currency=payment.currency,
                test=True,
                metadata={
                    "payment_id": str(payment.id),
                    "order_id": str(payment.order_id),
                },
            )
        remote = await self._provider.get_payment(payment.external_id)
        self._verify_provider_payment(payment, remote)
        if remote.status != "succeeded":
            raise InvalidPaymentState("Provider payment is not refundable")
        return remote

    async def refund_payment(
        self,
        payment_id: uuid.UUID,
        reason: str = "order_cancelled_compensation",
        *,
        commit: bool = True,
    ) -> PaymentModel:
        """Create an idempotent full provider refund and emit PaymentRefunded on success."""
        payment = await self._payment_repo.get_by_id_for_update(payment_id)
        if payment is None:
            raise PaymentNotFound
        if payment.status == PaymentStatus.REFUNDED:
            return payment
        if payment.status != PaymentStatus.SUCCESS:
            raise InvalidPaymentState(f"Cannot refund payment in status {payment.status}")

        remote = await self._remote_for_refund(payment)
        refund = await self._provider.create_refund(
            payment=remote,
            idempotency_key=f"refund-{payment.id}",
            reason=reason,
        )
        self._verify_refund(payment, refund)
        if refund.status == "canceled":
            raise PaymentProviderRejected(
                refund.cancellation_reason or "Payment provider canceled the refund"
            )
        await self._finish_refund(payment, refund, reason=reason)
        await self._payment_repo.update(payment)
        if commit:
            await self._session.commit()
            await self._session.refresh(payment)
        return payment

    async def reconcile_refund(self, external_id: str) -> PaymentModel:
        """Apply a verified asynchronous refund status."""
        refund = await self._provider.get_refund(external_id)
        if refund.id != external_id:
            raise PaymentVerificationFailed("Provider refund identifier does not match")
        payment = await self._payment_repo.get_by_external_id_for_update(refund.payment_id)
        if payment is None:
            raise PaymentVerificationFailed("Refunded payment was not found")
        self._verify_refund(payment, refund)
        await self._finish_refund(payment, refund, reason="provider_refund_succeeded")
        await self._payment_repo.update(payment)
        await self._session.commit()
        await self._session.refresh(payment)
        return payment

    async def confirm_payment(self, payment_id: uuid.UUID) -> PaymentModel:
        """Mark a mock payment successful for administrative test workflows."""
        if self._provider_name != "mock":
            raise InvalidPaymentState("Manual confirmation is only available for mock payments")
        payment = await self._payment_repo.get_by_id_for_update(payment_id)
        if payment is None:
            raise PaymentNotFound
        if payment.status != PaymentStatus.PENDING:
            raise InvalidPaymentState("Payment is not pending")
        self._ensure_not_expired(payment)

        payment.status = PaymentStatus.SUCCESS
        payment.external_id = payment.external_id or f"mock-{payment.id}"
        payment.external_status = "succeeded"
        payment.provider_test = True
        await self._payment_repo.update(payment)
        await self._emit_succeeded(payment)
        await self._session.commit()
        await self._session.refresh(payment)
        return payment

    async def fail_payment(self, payment_id: uuid.UUID) -> PaymentModel:
        """Mark a mock payment failed for administrative test workflows."""
        if self._provider_name != "mock":
            raise InvalidPaymentState("Manual failure is only available for mock payments")
        payment = await self._payment_repo.get_by_id_for_update(payment_id)
        if payment is None:
            raise PaymentNotFound
        if payment.status != PaymentStatus.PENDING:
            raise InvalidPaymentState("Payment is not pending")

        payment.status = PaymentStatus.FAILED
        payment.external_status = "canceled"
        payment.cancellation_reason = "provider_declined"
        await self._payment_repo.update(payment)
        await self._emit_failed(payment, "provider_declined")
        await self._session.commit()
        await self._session.refresh(payment)
        return payment

    async def cancel_payment(self, payment_id: uuid.UUID) -> PaymentModel:
        """Cancel a pending local mock payment and emit an event."""
        if self._provider_name != "mock":
            raise InvalidPaymentState("Provider payments cannot be canceled locally")
        payment = await self._payment_repo.get_by_id_for_update(payment_id)
        if payment is None:
            raise PaymentNotFound
        if payment.status != PaymentStatus.PENDING:
            raise InvalidPaymentState("Payment is not pending")

        payment.status = PaymentStatus.CANCELLED
        await self._payment_repo.update(payment)
        payload = {
            "payment_id": str(payment.id),
            "order_id": str(payment.order_id),
            "user_id": str(payment.user_id),
            "amount": payment.amount,
            "currency": payment.currency,
        }
        await self._outbox_repo.add(
            PaymentEventType.PAYMENT_CANCELLED,
            json.dumps(payload, separators=(",", ":")),
        )
        await self._session.commit()
        await self._session.refresh(payment)
        return payment

    async def get_payment(self, payment_id: uuid.UUID) -> PaymentModel:
        """Return a payment by id."""
        payment = await self._payment_repo.get_by_id(payment_id)
        if payment is None:
            raise PaymentNotFound
        return payment

    async def get_payment_by_order_id(self, order_id: uuid.UUID) -> PaymentModel:
        """Return an order's authoritative payment or signal eventual-consistency delay."""
        payment = await self._payment_repo.get_by_order_id(order_id)
        if payment is None:
            raise PaymentNotReady
        return payment

    async def list_user_payments(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> tuple[list[PaymentModel], int]:
        """Return a paginated list of a user's payments."""
        items = await self._payment_repo.list_by_user(user_id, limit=limit, offset=offset)
        total = await self._payment_repo.count_by_user(user_id)
        return list(items), total
