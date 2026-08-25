"""Payment application service."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.contracts import PaymentProvider, ProviderPayment, ProviderRefund
from payments.application.schemas import CreatePaymentRequest
from payments.domain.entities import (
    PaymentEventType,
    PaymentStatus,
    ProviderOperationStatus,
)
from payments.domain.exceptions import (
    InvalidPaymentState,
    PaymentNotFound,
    PaymentNotReady,
    PaymentProviderRejected,
    PaymentProviderResultUnknown,
    PaymentProviderUnavailable,
    PaymentVerificationFailed,
)
from payments.infrastructure.database import utc_now
from payments.infrastructure.models import PaymentModel, ProviderOperationModel
from payments.infrastructure.repositories.payment import (
    OutboxRepository,
    PaymentRepository,
    ProviderOperationRepository,
)


class PaymentService:
    """Orchestrate the local lifecycle and the configured payment provider."""

    def __init__(
        self,
        session: AsyncSession,
        payment_repo: PaymentRepository,
        outbox_repo: OutboxRepository,
        operation_repo: ProviderOperationRepository | None = None,
        provider: PaymentProvider | None = None,
        *,
        provider_name: str = "mock",
        return_url: str = "http://localhost/payment/return",
        test_mode_required: bool = True,
    ) -> None:
        self._session = session
        self._payment_repo = payment_repo
        self._outbox_repo = outbox_repo
        self._operation_repo = operation_repo or ProviderOperationRepository(session)
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
        # The authorization lookup in the route may have opened an implicit transaction.
        # Release it before claiming the short write phase below.
        await self._session.rollback()
        payment = await self._payment_repo.get_by_order_id_for_update(order_id)
        if payment is None:
            raise PaymentNotReady
        if payment.status != PaymentStatus.PENDING:
            raise InvalidPaymentState(f"Cannot pay an order in status {payment.status}")
        if payment.provider != self._provider_name:
            raise InvalidPaymentState("Payment provider configuration changed")
        self._ensure_not_expired(payment)
        if payment.confirmation_url:
            await self._session.commit()
            return payment

        request_payload = self._checkout_request_payload(payment)
        canonical_payload = json.dumps(
            request_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        request_hash = sha256(canonical_payload.encode()).hexdigest()
        operation = await self._operation_repo.get_by_type_and_entity(
            "create_payment",
            payment.id,
            for_update=True,
        )
        if operation is None:
            operation = ProviderOperationModel(
                operation_type="create_payment",
                entity_id=payment.id,
                payment_id=payment.id,
                idempotency_key=f"payment-{payment.id}",
                request_payload=canonical_payload,
                request_hash=request_hash,
            )
            await self._operation_repo.create(operation)
        elif operation.request_hash != request_hash:
            operation.status = ProviderOperationStatus.QUARANTINED
            operation.last_error_code = "idempotency_payload_mismatch"
            await self._session.commit()
            raise PaymentVerificationFailed("Provider operation payload changed")
        elif operation.status in {
            ProviderOperationStatus.IN_FLIGHT,
            ProviderOperationStatus.UNKNOWN,
        }:
            operation.status = ProviderOperationStatus.UNKNOWN
            operation.last_error_code = "previous_result_unknown"
            await self._session.commit()
            raise PaymentProviderResultUnknown
        elif operation.status == ProviderOperationStatus.QUARANTINED:
            await self._session.commit()
            raise PaymentProviderResultUnknown
        elif operation.status == ProviderOperationStatus.FAILED:
            await self._session.commit()
            raise PaymentProviderRejected("Payment creation was rejected")

        now = utc_now()
        operation.status = ProviderOperationStatus.IN_FLIGHT
        operation.attempt_count += 1
        operation.first_requested_at = operation.first_requested_at or now
        operation.last_attempt_at = now
        operation.next_attempt_at = None
        operation_id = operation.id
        payment_id = payment.id
        amount = payment.amount
        currency = payment.currency
        description = f"FlashMarket order {payment.order_id}"
        return_url = str(request_payload["return_url"])
        idempotency_key = operation.idempotency_key
        await self._session.commit()

        try:
            remote = await self._provider.create_payment(
                payment_id=payment_id,
                order_id=order_id,
                amount=amount,
                currency=currency,
                description=description,
                return_url=return_url,
                idempotency_key=idempotency_key,
            )
        except PaymentProviderUnavailable as exc:
            await self._finish_provider_operation(
                operation_id,
                status=ProviderOperationStatus.UNKNOWN,
                error_code=exc.code,
            )
            raise PaymentProviderResultUnknown from exc
        except PaymentProviderRejected as exc:
            await self._finish_provider_operation(
                operation_id,
                status=ProviderOperationStatus.FAILED,
                error_code=exc.code,
            )
            raise

        locked = await self._payment_repo.get_by_id_for_update(payment_id)
        if locked is None:
            raise PaymentNotFound
        if locked.confirmation_url:
            await self._session.commit()
            return locked
        locked_operation = await self._operation_repo.get_by_id_for_update(operation_id)
        if locked_operation is None:
            raise PaymentVerificationFailed("Provider operation was not found")
        try:
            self._verify_provider_payment(locked, remote, require_confirmation=True)
        except PaymentVerificationFailed, PaymentProviderRejected:
            locked_operation.status = ProviderOperationStatus.QUARANTINED
            locked_operation.external_id = remote.id
            locked_operation.last_error_code = "provider_verification_failed"
            locked_operation.response_payload = self._provider_payment_snapshot(remote)
            await self._session.commit()
            raise
        locked.external_id = remote.id
        locked.external_status = remote.status
        locked.confirmation_url = remote.confirmation_url
        locked.provider_test = remote.test
        locked.cancellation_reason = remote.cancellation_reason
        locked_operation.status = ProviderOperationStatus.SUCCEEDED
        locked_operation.external_id = remote.id
        locked_operation.last_error_code = None
        locked_operation.response_payload = self._provider_payment_snapshot(remote)
        await self._payment_repo.update(locked)
        await self._operation_repo.update(locked_operation)
        await self._session.commit()
        await self._session.refresh(locked)
        return locked

    def _checkout_request_payload(self, payment: PaymentModel) -> dict[str, object]:
        return_url = (
            f"{self._return_url}{'&' if '?' in self._return_url else '?'}"
            f"order_id={payment.order_id}"
        )
        return {
            "payment_id": str(payment.id),
            "order_id": str(payment.order_id),
            "amount": payment.amount,
            "currency": payment.currency,
            "description": f"FlashMarket order {payment.order_id}",
            "return_url": return_url,
        }

    @staticmethod
    def _provider_payment_snapshot(remote: ProviderPayment) -> str:
        return json.dumps(
            {
                "id": remote.id,
                "status": remote.status,
                "amount": remote.amount,
                "currency": remote.currency,
                "test": remote.test,
                "metadata": remote.metadata,
                "confirmation_url": remote.confirmation_url,
                "cancellation_reason": remote.cancellation_reason,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    async def _finish_provider_operation(
        self,
        operation_id: uuid.UUID,
        *,
        status: ProviderOperationStatus,
        error_code: str,
    ) -> None:
        await self._session.rollback()
        operation = await self._operation_repo.get_by_id_for_update(operation_id)
        if operation is None:
            return
        operation.status = status
        operation.last_error_code = error_code
        await self._operation_repo.update(operation)
        await self._session.commit()

    async def reconcile_unknown_operations(self, *, limit: int = 20) -> int:
        """Recover a bounded batch of uncertain creates without repeating their POST."""
        claim_token, claimed = await self._operation_repo.claim_due_unknown(limit=limit)
        operation_ids = [operation.id for operation in claimed]
        await self._session.commit()
        for operation_id in operation_ids:
            await self._recover_unknown_operation(operation_id, claim_token)
        return len(operation_ids)

    async def _recover_unknown_operation(
        self,
        operation_id: uuid.UUID,
        claim_token: uuid.UUID,
    ) -> None:
        operation = await self._operation_repo.get_by_id_for_update(operation_id)
        if operation is None or operation.claim_token != claim_token:
            await self._session.rollback()
            return
        if operation.operation_type != "create_payment":
            await self._quarantine_operation(operation, "unsupported_recovery_operation")
            return
        payment_id = operation.payment_id
        external_id = operation.external_id
        first_requested_at = operation.first_requested_at or operation.created_at
        if first_requested_at.tzinfo is None:
            first_requested_at = first_requested_at.replace(tzinfo=UTC)
        await self._session.commit()

        try:
            remote: ProviderPayment | None
            if external_id is not None:
                remote = await self._provider.get_payment(external_id)
            else:
                remote = await self._find_created_payment(
                    payment_id,
                    first_requested_at=first_requested_at,
                )
        except PaymentProviderUnavailable as exc:
            await self._reschedule_unknown_operation(
                operation_id,
                claim_token,
                error_code=exc.code,
                first_requested_at=first_requested_at,
            )
            return
        except PaymentVerificationFailed:
            operation = await self._operation_repo.get_by_id_for_update(operation_id)
            if operation is not None and operation.claim_token == claim_token:
                await self._quarantine_operation(operation, "ambiguous_or_mismatched_payment")
            return

        if remote is None:
            await self._reschedule_unknown_operation(
                operation_id,
                claim_token,
                error_code="provider_payment_not_found",
                first_requested_at=first_requested_at,
            )
            return

        try:
            await self.reconcile_payment(remote)
        except PaymentVerificationFailed:
            operation = await self._operation_repo.get_by_id_for_update(operation_id)
            if operation is not None and operation.claim_token == claim_token:
                await self._quarantine_operation(operation, "provider_verification_failed")
            return

        operation = await self._operation_repo.get_by_id_for_update(operation_id)
        if operation is None or operation.claim_token != claim_token:
            await self._session.rollback()
            return
        operation.status = ProviderOperationStatus.SUCCEEDED
        operation.external_id = remote.id
        operation.response_payload = self._provider_payment_snapshot(remote)
        operation.last_error_code = None
        operation.claim_token = None
        operation.claimed_until = None
        await self._session.commit()

    async def _find_created_payment(
        self,
        payment_id: uuid.UUID,
        *,
        first_requested_at: datetime,
    ) -> ProviderPayment | None:
        requested_at = first_requested_at
        cursor: str | None = None
        matches: list[ProviderPayment] = []
        for _ in range(5):
            page = await self._provider.list_payments(
                created_gte=requested_at - timedelta(minutes=5),
                created_lte=requested_at + timedelta(minutes=5),
                limit=100,
                cursor=cursor,
            )
            matches.extend(
                candidate
                for candidate in page.items
                if candidate.metadata.get("payment_id") == str(payment_id)
            )
            if len(matches) > 1 or page.next_cursor is None:
                break
            cursor = page.next_cursor
        if len(matches) > 1:
            raise PaymentVerificationFailed("Multiple provider payments matched one operation")
        return matches[0] if matches else None

    async def _reschedule_unknown_operation(
        self,
        operation_id: uuid.UUID,
        claim_token: uuid.UUID,
        *,
        error_code: str,
        first_requested_at: datetime,
    ) -> None:
        operation = await self._operation_repo.get_by_id_for_update(operation_id)
        if operation is None or operation.claim_token != claim_token:
            await self._session.rollback()
            return
        requested_at = first_requested_at
        if utc_now() - requested_at >= timedelta(hours=24):
            await self._quarantine_operation(operation, f"idempotency_expired:{error_code}")
            return
        delay_seconds = min(30 * (2 ** min(operation.attempt_count, 6)), 900)
        operation.status = ProviderOperationStatus.UNKNOWN
        operation.next_attempt_at = utc_now() + timedelta(seconds=delay_seconds)
        operation.last_error_code = error_code
        operation.claim_token = None
        operation.claimed_until = None
        await self._session.commit()

    async def _quarantine_operation(
        self,
        operation: ProviderOperationModel,
        error_code: str,
    ) -> None:
        operation.status = ProviderOperationStatus.QUARANTINED
        operation.last_error_code = error_code
        operation.next_attempt_at = None
        operation.claim_token = None
        operation.claimed_until = None
        await self._session.commit()

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
