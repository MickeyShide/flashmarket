"""Payment application service."""

from __future__ import annotations

import json
import random
import uuid
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.contracts import PaymentProvider, ProviderPayment, ProviderRefund
from payments.application.schemas import CreatePaymentRequest, YooKassaWebhook
from payments.domain.entities import (
    PaymentAttemptStatus,
    PaymentEventType,
    PaymentStatus,
    ProviderOperationStatus,
    RefundStatus,
    WebhookInboxStatus,
)
from payments.domain.exceptions import (
    InvalidPaymentState,
    PaymentNotFound,
    PaymentNotReady,
    PaymentProviderMalformedResponse,
    PaymentProviderRejected,
    PaymentProviderResultUnknown,
    PaymentProviderUnavailable,
    PaymentVerificationFailed,
)
from payments.infrastructure.database import utc_now
from payments.infrastructure.models import (
    FinancialLedgerModel,
    PaymentAttemptModel,
    PaymentModel,
    ProviderOperationModel,
    RefundModel,
    WebhookInboxModel,
)
from payments.infrastructure.repositories.payment import (
    FinancialLedgerRepository,
    OutboxRepository,
    PaymentAttemptRepository,
    PaymentRepository,
    ProviderOperationRepository,
    RefundRepository,
    WebhookInboxRepository,
)


class PaymentService:
    """Orchestrate the local lifecycle and the configured payment provider."""

    def __init__(
        self,
        session: AsyncSession,
        payment_repo: PaymentRepository,
        outbox_repo: OutboxRepository,
        operation_repo: ProviderOperationRepository | None = None,
        attempt_repo: PaymentAttemptRepository | None = None,
        webhook_repo: WebhookInboxRepository | None = None,
        refund_repo: RefundRepository | None = None,
        ledger_repo: FinancialLedgerRepository | None = None,
        provider: PaymentProvider | None = None,
        *,
        provider_name: str = "mock",
        return_url: str = "http://localhost/payment/return",
        test_mode_required: bool = True,
        webhook_max_attempts: int = 12,
        attempt_ttl_seconds: int = 1800,
    ) -> None:
        self._session = session
        self._payment_repo = payment_repo
        self._outbox_repo = outbox_repo
        self._operation_repo = operation_repo or ProviderOperationRepository(session)
        self._attempt_repo = attempt_repo or PaymentAttemptRepository(session)
        self._webhook_repo = webhook_repo or WebhookInboxRepository(session)
        self._refund_repo = refund_repo or RefundRepository(session)
        self._ledger_repo = ledger_repo or FinancialLedgerRepository(session)
        if provider is None:
            from payments.infrastructure.providers.mock import MockPaymentProvider

            provider = MockPaymentProvider()
        self._provider = provider
        self._provider_name = provider_name
        self._return_url = return_url
        self._test_mode_required = test_mode_required
        self._webhook_max_attempts = webhook_max_attempts
        self._attempt_ttl_seconds = attempt_ttl_seconds

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
        attempt: PaymentAttemptModel | None = None,
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
        if attempt is not None and remote.metadata.get("attempt_id") != str(attempt.id):
            raise PaymentVerificationFailed("Payment attempt metadata does not match")
        expected_external_id = attempt.external_id if attempt is not None else local.external_id
        if expected_external_id is not None and expected_external_id != remote.id:
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
        attempt = await self._attempt_repo.get_active_for_update(payment.id)
        if attempt is not None and self._attempt_expired(attempt):
            attempt.status = PaymentAttemptStatus.EXPIRED
            attempt = None
        if attempt is None:
            attempt_number = await self._attempt_repo.next_attempt_number(payment.id)
            attempt_expires_at = utc_now() + timedelta(seconds=self._attempt_ttl_seconds)
            if payment.expires_at is not None:
                payment_deadline = payment.expires_at
                if payment_deadline.tzinfo is None:
                    payment_deadline = payment_deadline.replace(tzinfo=UTC)
                attempt_expires_at = min(attempt_expires_at, payment_deadline)
            attempt = PaymentAttemptModel(
                payment_id=payment.id,
                attempt_number=attempt_number,
                amount=payment.amount,
                currency=payment.currency,
                provider=payment.provider,
                status=PaymentAttemptStatus.NEW,
                expires_at=attempt_expires_at,
            )
            try:
                await self._attempt_repo.create(attempt)
            except IntegrityError:
                await self._session.rollback()
                return await self.start_checkout(order_id)
            payment.current_attempt_id = attempt.id
            payment.current_attempt_status = attempt.status
            payment.external_id = None
            payment.external_status = None
            payment.confirmation_url = None
            payment.cancellation_reason = None
            payment.provider_test = None
        elif attempt.confirmation_url:
            self._sync_attempt_summary(payment, attempt)
            await self._session.commit()
            return payment

        request_payload = self._checkout_request_payload(payment, attempt)
        canonical_payload = json.dumps(
            request_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        request_hash = sha256(canonical_payload.encode()).hexdigest()
        operation = await self._operation_repo.get_by_type_and_entity(
            "create_payment",
            attempt.id,
            for_update=True,
        )
        if operation is None:
            operation = ProviderOperationModel(
                operation_type="create_payment",
                entity_id=attempt.id,
                payment_id=payment.id,
                idempotency_key=f"payment-{payment.id}-a{attempt.attempt_number}",
                request_payload=canonical_payload,
                request_hash=request_hash,
            )
            await self._operation_repo.create(operation)
        elif operation.request_hash != request_hash:
            operation.status = ProviderOperationStatus.QUARANTINED
            operation.last_error_code = "idempotency_payload_mismatch"
            await self._session.commit()
            raise PaymentVerificationFailed("Provider operation payload changed")
        elif operation.status == ProviderOperationStatus.IN_FLIGHT:
            await self._session.commit()
            raise PaymentProviderResultUnknown
        elif operation.status == ProviderOperationStatus.UNKNOWN:
            operation.status = ProviderOperationStatus.UNKNOWN
            operation.last_error_code = "previous_result_unknown"
            attempt.status = PaymentAttemptStatus.UNKNOWN
            await self._session.commit()
            raise PaymentProviderResultUnknown
        elif operation.status == ProviderOperationStatus.QUARANTINED:
            attempt.status = PaymentAttemptStatus.UNKNOWN
            await self._session.commit()
            raise PaymentProviderResultUnknown
        elif operation.status == ProviderOperationStatus.FAILED:
            attempt.status = PaymentAttemptStatus.FAILED
            await self._session.commit()
            raise PaymentProviderRejected("Payment creation was rejected")

        now = utc_now()
        attempt.status = PaymentAttemptStatus.PREPARING
        payment.current_attempt_status = attempt.status
        operation.status = ProviderOperationStatus.IN_FLIGHT
        operation.attempt_count += 1
        operation.first_requested_at = operation.first_requested_at or now
        operation.last_attempt_at = now
        operation.next_attempt_at = None
        operation.claimed_until = now + timedelta(seconds=60)
        operation_id = operation.id
        payment_id = payment.id
        attempt_id = attempt.id
        amount = payment.amount
        currency = payment.currency
        description = f"FlashMarket order {payment.order_id}"
        return_url = str(request_payload["return_url"])
        idempotency_key = operation.idempotency_key
        await self._session.commit()

        try:
            remote = await self._provider.create_payment(
                payment_id=payment_id,
                attempt_id=attempt_id,
                order_id=order_id,
                amount=amount,
                currency=currency,
                description=description,
                return_url=return_url,
                idempotency_key=idempotency_key,
            )
        except PaymentProviderMalformedResponse as exc:
            await self._finish_provider_operation(
                operation_id,
                status=ProviderOperationStatus.UNKNOWN,
                error_code=exc.code,
            )
            await self._mark_attempt_status(attempt_id, PaymentAttemptStatus.UNKNOWN)
            raise PaymentProviderResultUnknown from exc
        except PaymentProviderUnavailable as exc:
            await self._finish_provider_operation(
                operation_id,
                status=ProviderOperationStatus.UNKNOWN,
                error_code=exc.code,
            )
            await self._mark_attempt_status(attempt_id, PaymentAttemptStatus.UNKNOWN)
            raise PaymentProviderResultUnknown from exc
        except PaymentProviderRejected as exc:
            await self._finish_provider_operation(
                operation_id,
                status=ProviderOperationStatus.FAILED,
                error_code=exc.code,
            )
            await self._mark_attempt_status(attempt_id, PaymentAttemptStatus.FAILED)
            raise

        locked = await self._payment_repo.get_by_id_for_update(payment_id)
        if locked is None:
            raise PaymentNotFound
        locked_attempt = await self._attempt_repo.get_by_id_for_update(attempt_id)
        if locked_attempt is None:
            raise PaymentVerificationFailed("Payment attempt was not found")
        if locked_attempt.confirmation_url:
            self._sync_attempt_summary(locked, locked_attempt)
            await self._session.commit()
            return locked
        locked_operation = await self._operation_repo.get_by_id_for_update(operation_id)
        if locked_operation is None:
            raise PaymentVerificationFailed("Provider operation was not found")
        try:
            self._verify_provider_payment(
                locked,
                remote,
                attempt=locked_attempt,
                require_confirmation=True,
            )
        except (PaymentVerificationFailed, PaymentProviderRejected) as exc:
            locked_operation.status = ProviderOperationStatus.QUARANTINED
            locked_operation.external_id = remote.id
            locked_operation.last_error_code = "provider_verification_failed"
            locked_operation.response_payload = self._provider_payment_snapshot(remote)
            # A returned provider object proves the POST may have created a charge.
            # Keep the attempt active until an operator can resolve the mismatch.
            locked_attempt.status = PaymentAttemptStatus.UNKNOWN
            locked_attempt.cancellation_reason = "provider_verification_failed"
            locked_attempt.next_reconcile_at = None
            locked.current_attempt_status = PaymentAttemptStatus.UNKNOWN
            await self._session.commit()
            raise PaymentProviderResultUnknown from exc
        locked_attempt.external_id = remote.id
        locked_attempt.external_status = remote.status
        locked_attempt.confirmation_url = remote.confirmation_url
        locked_attempt.provider_test = remote.test
        locked_attempt.cancellation_reason = remote.cancellation_reason
        locked_attempt.expires_at = remote.expires_at or locked_attempt.expires_at
        locked_attempt.status = PaymentAttemptStatus.PENDING
        locked_attempt.next_reconcile_at = utc_now() + timedelta(
            seconds=random.uniform(30, 60)  # noqa: S311
        )
        self._sync_attempt_summary(locked, locked_attempt)
        locked_operation.status = ProviderOperationStatus.SUCCEEDED
        locked_operation.external_id = remote.id
        locked_operation.last_error_code = None
        locked_operation.response_payload = self._provider_payment_snapshot(remote)
        await self._payment_repo.update(locked)
        await self._operation_repo.update(locked_operation)
        await self._session.commit()
        await self._session.refresh(locked)
        return locked

    def _checkout_request_payload(
        self,
        payment: PaymentModel,
        attempt: PaymentAttemptModel,
    ) -> dict[str, object]:
        return_url = (
            f"{self._return_url}{'&' if '?' in self._return_url else '?'}"
            f"order_id={payment.order_id}"
        )
        return {
            "payment_id": str(payment.id),
            "attempt_id": str(attempt.id),
            "order_id": str(payment.order_id),
            "amount": payment.amount,
            "currency": payment.currency,
            "description": f"FlashMarket order {payment.order_id}",
            "return_url": return_url,
        }

    @staticmethod
    def _attempt_expired(attempt: PaymentAttemptModel) -> bool:
        if attempt.status != PaymentAttemptStatus.NEW or attempt.expires_at is None:
            return False
        expires_at = attempt.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return utc_now() >= expires_at

    @staticmethod
    def _sync_attempt_summary(
        payment: PaymentModel,
        attempt: PaymentAttemptModel,
    ) -> None:
        payment.current_attempt_id = attempt.id
        payment.current_attempt_status = attempt.status
        payment.external_id = attempt.external_id
        payment.external_status = attempt.external_status
        payment.confirmation_url = attempt.confirmation_url
        payment.provider_test = attempt.provider_test
        payment.cancellation_reason = attempt.cancellation_reason

    async def _mark_attempt_status(
        self,
        attempt_id: uuid.UUID,
        status: PaymentAttemptStatus,
    ) -> None:
        attempt = await self._attempt_repo.get_by_id_for_update(attempt_id)
        if attempt is None:
            await self._session.rollback()
            return
        attempt.status = status
        await self._session.commit()
        payment = await self._payment_repo.get_by_id_for_update(attempt.payment_id)
        if payment is not None and payment.current_attempt_id == attempt.id:
            payment.current_attempt_status = attempt.status
        await self._session.commit()

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
                "expires_at": remote.expires_at.isoformat() if remote.expires_at else None,
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
        operation.claim_token = None
        operation.claimed_until = None
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
        attempt_id = operation.entity_id
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
                    attempt_id=attempt_id,
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
        attempt_id: uuid.UUID,
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
                and candidate.metadata.get("attempt_id") == str(attempt_id)
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
        entity_id = operation.entity_id
        operation_type = operation.operation_type
        operation.status = ProviderOperationStatus.QUARANTINED
        operation.last_error_code = error_code
        operation.next_attempt_at = None
        operation.claim_token = None
        operation.claimed_until = None
        await self._session.commit()
        if operation_type == "create_payment":
            attempt = await self._attempt_repo.get_by_id_for_update(entity_id)
            if attempt is not None and attempt.status == PaymentAttemptStatus.UNKNOWN:
                # A bounded list miss is not evidence that the provider POST failed.
                # Retain the active slot and require manual resolution.
                attempt.next_reconcile_at = None
                attempt.cancellation_reason = error_code
                payment_id = attempt.payment_id
            else:
                payment_id = None
            await self._session.commit()
            if payment_id is not None:
                payment = await self._payment_repo.get_by_id_for_update(payment_id)
                if payment is not None and payment.current_attempt_id == entity_id:
                    payment.current_attempt_status = PaymentAttemptStatus.UNKNOWN
                    payment.cancellation_reason = error_code
                await self._session.commit()

    async def _emit_succeeded(self, payment: PaymentModel) -> None:
        if payment.external_id is None:
            raise PaymentVerificationFailed("Successful payment has no provider identifier")
        await self._ledger_repo.post(
            FinancialLedgerModel(
                payment_id=payment.id,
                entry_type="PAYMENT_CAPTURE",
                direction="CREDIT",
                amount=payment.amount,
                currency=payment.currency,
                provider_object_id=payment.external_id,
                event_key=f"payment_capture:{payment.external_id}",
                occurred_at=utc_now(),
            )
        )
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

    async def ingest_webhook(self, raw_body: bytes, *, source_ip: str | None) -> str:
        """Persist a notification before acknowledging it to the provider."""
        raw_text = raw_body.decode("utf-8", errors="replace")
        status = WebhookInboxStatus.PENDING
        last_error: str | None = None
        object_type: str | None = None
        external_id: str | None = None
        event: str | None = None
        target_status: str | None = None
        try:
            notification = YooKassaWebhook.model_validate_json(raw_body)
            event = notification.event
            external_raw = notification.object.get("id")
            status_raw = notification.object.get("status")
            if notification.type != "notification":
                raise ValueError("invalid_notification_type")
            if not isinstance(external_raw, str) or not external_raw:
                raise ValueError("missing_object_id")
            object_type, separator, event_status = event.partition(".")
            if not separator or object_type not in {"payment", "refund"}:
                raise ValueError("unsupported_event")
            external_id = external_raw
            target_status = str(status_raw) if status_raw is not None else event_status
            supported = event in {
                "payment.succeeded",
                "payment.canceled",
                "refund.succeeded",
            }
            if not supported:
                status = WebhookInboxStatus.PROCESSED
                last_error = "unsupported_event"
        except (ValidationError, ValueError) as exc:
            status = WebhookInboxStatus.QUARANTINED
            last_error = "malformed_notification" if isinstance(exc, ValidationError) else str(exc)

        semantic = {
            "provider": self._provider_name,
            "object_type": object_type,
            "external_id": external_id,
            "event": event,
            "target_status": target_status,
        }
        if external_id is None:
            semantic["raw_hash"] = sha256(raw_body).hexdigest()
        dedupe_hash = sha256(
            json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        item = WebhookInboxModel(
            provider=self._provider_name,
            object_type=object_type,
            external_id=external_id,
            event=event,
            target_status=target_status,
            dedupe_hash=dedupe_hash,
            raw_body=raw_text,
            source_ip=source_ip,
            status=status,
            last_error_code=last_error,
            processed_at=utc_now() if status == WebhookInboxStatus.PROCESSED else None,
        )
        try:
            await self._webhook_repo.create(item)
            await self._session.commit()
            return "accepted" if status == WebhookInboxStatus.PENDING else "acknowledged"
        except IntegrityError:
            await self._session.rollback()
            existing = await self._webhook_repo.get_by_dedupe_hash(dedupe_hash)
            if existing is None:
                raise
            return "duplicate"

    async def process_webhook_inbox(self, *, limit: int = 50) -> int:
        """Verify and apply a bounded batch of durably accepted notifications."""
        claim_token, claimed = await self._webhook_repo.claim_due(limit=limit)
        item_ids = [item.id for item in claimed]
        await self._session.commit()
        for item_id in item_ids:
            await self._process_webhook_item(item_id, claim_token)
        return len(item_ids)

    async def _process_webhook_item(
        self,
        item_id: uuid.UUID,
        claim_token: uuid.UUID,
    ) -> None:
        item = await self._webhook_repo.get_by_id_for_update(item_id)
        if item is None or item.claim_token != claim_token:
            await self._session.rollback()
            return
        object_type = item.object_type
        external_id = item.external_id
        await self._session.commit()
        if external_id is None:
            await self._finish_webhook_item(
                item_id,
                claim_token,
                status=WebhookInboxStatus.QUARANTINED,
                error_code="missing_object_id",
            )
            return
        try:
            if object_type == "payment":
                await self.reconcile_external_payment(external_id)
            elif object_type == "refund":
                await self.reconcile_refund(external_id)
            else:
                raise PaymentVerificationFailed("Unsupported webhook object")
        except PaymentProviderUnavailable as exc:
            await self._retry_webhook_item(item_id, claim_token, error_code=exc.code)
            return
        except (PaymentVerificationFailed, PaymentProviderRejected) as exc:
            await self._finish_webhook_item(
                item_id,
                claim_token,
                status=WebhookInboxStatus.QUARANTINED,
                error_code=exc.code,
            )
            return
        await self._finish_webhook_item(
            item_id,
            claim_token,
            status=WebhookInboxStatus.PROCESSED,
            error_code=None,
        )

    async def _retry_webhook_item(
        self,
        item_id: uuid.UUID,
        claim_token: uuid.UUID,
        *,
        error_code: str,
    ) -> None:
        item = await self._webhook_repo.get_by_id_for_update(item_id)
        if item is None or item.claim_token != claim_token:
            await self._session.rollback()
            return
        if item.attempt_count >= self._webhook_max_attempts:
            await self._finish_webhook_item(
                item_id,
                claim_token,
                status=WebhookInboxStatus.QUARANTINED,
                error_code=f"retry_exhausted:{error_code}",
            )
            return
        ceiling = min(5 * (2 ** min(item.attempt_count, 7)), 900)
        delay = random.uniform(ceiling / 2, ceiling)  # noqa: S311
        item.status = WebhookInboxStatus.RETRY
        item.next_attempt_at = utc_now() + timedelta(seconds=delay)
        item.last_error_code = error_code
        item.claim_token = None
        item.claimed_until = None
        await self._session.commit()

    async def _finish_webhook_item(
        self,
        item_id: uuid.UUID,
        claim_token: uuid.UUID,
        *,
        status: WebhookInboxStatus,
        error_code: str | None,
    ) -> None:
        item = await self._webhook_repo.get_by_id_for_update(item_id)
        if item is None or item.claim_token != claim_token:
            await self._session.rollback()
            return
        item.status = status
        item.last_error_code = error_code
        item.next_attempt_at = None
        item.claim_token = None
        item.claimed_until = None
        item.processed_at = utc_now()
        await self._session.commit()

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
        attempt: PaymentAttemptModel | None = None
        attempt_id_raw = remote.metadata.get("attempt_id")
        if attempt_id_raw:
            try:
                attempt_id = uuid.UUID(attempt_id_raw)
            except ValueError as exc:
                raise PaymentVerificationFailed("Payment attempt metadata is invalid") from exc
            attempt = await self._attempt_repo.get_by_id_for_update(attempt_id)
            if attempt is None or attempt.payment_id != payment.id:
                raise PaymentVerificationFailed("Local payment attempt was not found")
        elif payment.current_attempt_id is not None:
            attempt = await self._attempt_repo.get_by_id_for_update(payment.current_attempt_id)
        self._verify_provider_payment(payment, remote, attempt=attempt)

        if attempt is not None:
            attempt.external_id = remote.id
            attempt.external_status = remote.status
            attempt.provider_test = remote.test
            attempt.cancellation_reason = remote.cancellation_reason
            attempt.expires_at = remote.expires_at or attempt.expires_at
            if remote.confirmation_url:
                attempt.confirmation_url = remote.confirmation_url
        else:
            payment.external_id = remote.id
            payment.external_status = remote.status
            payment.provider_test = remote.test
            payment.cancellation_reason = remote.cancellation_reason

        if remote.status == "succeeded":
            if attempt is not None:
                attempt.status = PaymentAttemptStatus.SUCCEEDED
                attempt.next_reconcile_at = None
                attempt.claim_token = None
                attempt.claimed_until = None
                self._sync_attempt_summary(payment, attempt)
            if payment.status not in (PaymentStatus.SUCCESS, PaymentStatus.REFUNDED):
                payment.status = PaymentStatus.SUCCESS
                await self._emit_succeeded(payment)
        elif remote.status == "canceled":
            if attempt is not None:
                attempt.status = PaymentAttemptStatus.CANCELED
                attempt.next_reconcile_at = None
                attempt.claim_token = None
                attempt.claimed_until = None
                if payment.current_attempt_id == attempt.id:
                    self._sync_attempt_summary(payment, attempt)
            expires_at = payment.expires_at
            if expires_at is not None and expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if (
                payment.status == PaymentStatus.PENDING
                and expires_at is not None
                and utc_now() >= expires_at
            ):
                payment.status = PaymentStatus.FAILED
                await self._emit_failed(
                    payment,
                    remote.cancellation_reason or "provider_cancelled",
                )
        elif attempt is not None:
            attempt.status = PaymentAttemptStatus.PENDING
            attempt.next_reconcile_at = utc_now() + timedelta(
                seconds=random.uniform(30, 60)  # noqa: S311
            )
            attempt.claim_token = None
            attempt.claimed_until = None
            if payment.current_attempt_id == attempt.id:
                self._sync_attempt_summary(payment, attempt)

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

    async def reconcile_active_attempts(self, *, limit: int = 20) -> int:
        """Poll a leased, bounded batch of active provider payments."""
        claim_token, claimed = await self._attempt_repo.claim_due(limit=limit)
        snapshots = [(attempt.id, attempt.external_id) for attempt in claimed]
        await self._session.commit()
        for attempt_id, external_id in snapshots:
            if external_id is None:
                continue
            try:
                remote = await self._provider.get_payment(external_id)
                if remote.id != external_id:
                    raise PaymentVerificationFailed("Provider payment identifier does not match")
                await self.reconcile_payment(remote)
            except PaymentProviderUnavailable as exc:
                await self._reschedule_attempt(attempt_id, claim_token, exc.code)
            except PaymentProviderRejected, PaymentVerificationFailed:
                await self._quarantine_attempt(attempt_id, claim_token)
        return len(snapshots)

    async def _reschedule_attempt(
        self,
        attempt_id: uuid.UUID,
        claim_token: uuid.UUID,
        error_code: str,
    ) -> None:
        attempt = await self._attempt_repo.get_by_id_for_update(attempt_id)
        if attempt is None or attempt.claim_token != claim_token:
            await self._session.rollback()
            return
        ceiling = min(15 * (2 ** min(attempt.reconcile_attempt_count, 6)), 900)
        attempt.next_reconcile_at = utc_now() + timedelta(
            seconds=random.uniform(ceiling / 2, ceiling)  # noqa: S311
        )
        attempt.cancellation_reason = error_code
        attempt.claim_token = None
        attempt.claimed_until = None
        await self._session.commit()

    async def _quarantine_attempt(
        self,
        attempt_id: uuid.UUID,
        claim_token: uuid.UUID,
    ) -> None:
        attempt = await self._attempt_repo.get_by_id_for_update(attempt_id)
        if attempt is None or attempt.claim_token != claim_token:
            await self._session.rollback()
            return
        # Verification failure does not prove that the remote payment cannot
        # still succeed. Keep the attempt active and block a second charge.
        attempt.status = PaymentAttemptStatus.UNKNOWN
        attempt.cancellation_reason = "reconciliation_verification_failed"
        attempt.next_reconcile_at = None
        attempt.claim_token = None
        attempt.claimed_until = None
        payment = await self._payment_repo.get_by_id_for_update(attempt.payment_id)
        if payment is not None and payment.current_attempt_id == attempt.id:
            self._sync_attempt_summary(payment, attempt)
        await self._session.commit()

    @staticmethod
    def _verify_refund(
        payment: PaymentModel,
        refund: ProviderRefund,
        *,
        expected_amount: int,
    ) -> None:
        if payment.external_id != refund.payment_id:
            raise PaymentVerificationFailed("Refund payment identifier does not match")
        if expected_amount != refund.amount or payment.currency != refund.currency:
            raise PaymentVerificationFailed("Refund amount or currency does not match")

    @staticmethod
    def _provider_refund_snapshot(remote: ProviderRefund) -> str:
        return json.dumps(
            {
                "id": remote.id,
                "payment_id": remote.payment_id,
                "status": remote.status,
                "amount": remote.amount,
                "currency": remote.currency,
                "cancellation_reason": remote.cancellation_reason,
            },
            sort_keys=True,
            separators=(",", ":"),
        )

    async def _finish_refund(
        self,
        payment: PaymentModel,
        local_refund: RefundModel,
        remote_refund: ProviderRefund,
    ) -> None:
        local_refund.external_id = remote_refund.id
        local_refund.external_status = remote_refund.status
        local_refund.cancellation_reason = remote_refund.cancellation_reason
        local_refund.claim_token = None
        local_refund.claimed_until = None
        payment.refund_external_id = remote_refund.id
        payment.refund_status = remote_refund.status
        if remote_refund.status == "canceled":
            reason = remote_refund.cancellation_reason or "provider_cancelled"
            local_refund.funds_reserved = False
            local_refund.status = (
                RefundStatus.CANCELED
                if reason == "rejected_by_timeout"
                else RefundStatus.QUARANTINED
            )
            if reason == "rejected_by_timeout":
                local_refund.next_attempt_at = utc_now() + timedelta(seconds=30)
            return
        if remote_refund.status != "succeeded":
            local_refund.funds_reserved = True
            local_refund.status = RefundStatus.PENDING
            return
        if local_refund.status == RefundStatus.SUCCEEDED:
            return
        local_refund.funds_reserved = True
        local_refund.status = RefundStatus.SUCCEEDED
        await self._ledger_repo.post(
            FinancialLedgerModel(
                payment_id=payment.id,
                refund_id=local_refund.id,
                entry_type="REFUND",
                direction="DEBIT",
                amount=local_refund.amount,
                currency=local_refund.currency,
                provider_object_id=remote_refund.id,
                event_key=f"refund:{remote_refund.id}",
                occurred_at=utc_now(),
            )
        )
        total_refunded = await self._refund_repo.succeeded_amount(payment.id)
        if total_refunded >= payment.amount:
            payment.status = PaymentStatus.REFUNDED
        payload = {
            "payment_id": str(payment.id),
            "refund_id": str(local_refund.id),
            "order_id": str(payment.order_id),
            "user_id": str(payment.user_id),
            "amount": local_refund.amount,
            "currency": local_refund.currency,
            "reason": local_refund.reason,
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
        amount: int | None = None,
        request_id: str | None = None,
        commit: bool = True,
    ) -> PaymentModel:
        """Reserve and create an idempotent full or partial provider refund."""
        del commit  # The split transaction flow always owns its safe commit boundaries.
        payment = await self._payment_repo.get_by_id_for_update(payment_id)
        if payment is None:
            raise PaymentNotFound
        if payment.status == PaymentStatus.REFUNDED:
            return payment
        if payment.status != PaymentStatus.SUCCESS:
            raise InvalidPaymentState(f"Cannot refund payment in status {payment.status}")
        if request_id is None:
            prior = await self._refund_repo.get_latest_by_reason(payment.id, reason)
            if prior is not None and prior.funds_reserved:
                payment.refund_external_id = prior.external_id
                payment.refund_status = prior.external_status or prior.status
                await self._session.commit()
                return payment
        reserved = await self._refund_repo.reserved_amount(payment.id)
        refundable = payment.amount - reserved
        requested_amount = refundable if amount is None else amount
        if requested_amount <= 0 or requested_amount > refundable:
            raise InvalidPaymentState("Refund exceeds the available captured balance")
        request_key = sha256(
            f"{payment.id}:{request_id or reason}:{requested_amount}".encode()
        ).hexdigest()
        existing = await self._refund_repo.get_by_request_key(request_key)
        if existing is not None:
            payment.refund_external_id = existing.external_id
            payment.refund_status = existing.external_status or existing.status
            await self._session.commit()
            return payment

        local_refund = RefundModel(
            payment_id=payment.id,
            request_key=request_key,
            amount=requested_amount,
            currency=payment.currency,
            reason=reason,
            status=RefundStatus.NEW,
            funds_reserved=True,
            claimed_until=utc_now() + timedelta(seconds=60),
        )
        await self._refund_repo.create(local_refund)
        canonical_payload = json.dumps(
            {
                "payment_id": str(payment.id),
                "provider_payment_id": payment.external_id,
                "amount": requested_amount,
                "currency": payment.currency,
                "reason": reason,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        operation = ProviderOperationModel(
            operation_type="create_refund",
            entity_id=local_refund.id,
            payment_id=payment.id,
            idempotency_key=f"refund-{local_refund.id}",
            request_payload=canonical_payload,
            request_hash=sha256(canonical_payload.encode()).hexdigest(),
        )
        await self._operation_repo.create(operation)
        refund_id = local_refund.id
        operation_id = operation.id
        await self._session.commit()
        return await self._submit_refund(refund_id, operation_id)

    async def _submit_refund(
        self,
        refund_id: uuid.UUID,
        operation_id: uuid.UUID,
    ) -> PaymentModel:
        refund_snapshot = await self._refund_repo.get_by_id(refund_id)
        if refund_snapshot is None:
            raise PaymentVerificationFailed("Refund was not found")
        payment_snapshot = await self._payment_repo.get_by_id(refund_snapshot.payment_id)
        if payment_snapshot is None or payment_snapshot.external_id is None:
            raise PaymentVerificationFailed("Refund payment was not found")
        payment_id = payment_snapshot.id
        external_id = payment_snapshot.external_id
        amount = refund_snapshot.amount
        reason = refund_snapshot.reason
        if self._provider_name == "mock":
            remote_payment = ProviderPayment(
                id=external_id,
                status="succeeded",
                amount=payment_snapshot.amount,
                currency=payment_snapshot.currency,
                test=True,
                metadata={
                    "payment_id": str(payment_snapshot.id),
                    "order_id": str(payment_snapshot.order_id),
                },
            )
            await self._session.rollback()
        else:
            await self._session.rollback()
            try:
                remote_payment = await self._provider.get_payment(external_id)
            except PaymentProviderUnavailable as exc:
                retry_refund = await self._refund_repo.get_by_id_for_update(refund_id)
                if retry_refund is not None:
                    retry_refund.status = RefundStatus.NEW
                    retry_refund.next_attempt_at = utc_now() + timedelta(seconds=30)
                    retry_refund.claim_token = None
                    retry_refund.claimed_until = None
                    await self._session.commit()
                raise exc

        payment_check = await self._payment_repo.get_by_id_for_update(payment_id)
        if payment_check is None:
            raise PaymentVerificationFailed("Refund payment was not found")
        self._verify_provider_payment(payment_check, remote_payment)
        if remote_payment.status != "succeeded":
            raise InvalidPaymentState("Provider payment is not refundable")
        locked_operation = await self._operation_repo.get_by_id_for_update(operation_id)
        locked_refund = await self._refund_repo.get_by_id_for_update(refund_id)
        if locked_operation is None or locked_refund is None:
            raise PaymentVerificationFailed("Refund operation was not found")
        now = utc_now()
        locked_operation.status = ProviderOperationStatus.IN_FLIGHT
        locked_operation.attempt_count += 1
        locked_operation.first_requested_at = locked_operation.first_requested_at or now
        locked_operation.last_attempt_at = now
        locked_operation.claimed_until = now + timedelta(seconds=60)
        locked_refund.status = RefundStatus.PREPARING
        locked_refund.funds_reserved = True
        locked_refund.attempt_count += 1
        await self._session.commit()
        try:
            remote_refund = await self._provider.create_refund(
                payment=remote_payment,
                amount=amount,
                idempotency_key=locked_operation.idempotency_key,
                reason=reason,
            )
        except PaymentProviderMalformedResponse as exc:
            await self._finish_provider_operation(
                operation_id,
                status=ProviderOperationStatus.UNKNOWN,
                error_code=exc.code,
            )
            uncertain_refund = await self._refund_repo.get_by_id_for_update(refund_id)
            if uncertain_refund is not None:
                uncertain_refund.status = RefundStatus.UNKNOWN
                uncertain_refund.funds_reserved = True
                uncertain_refund.claim_token = None
                uncertain_refund.claimed_until = None
                await self._session.commit()
            raise PaymentProviderResultUnknown from exc
        except PaymentProviderUnavailable as exc:
            await self._finish_provider_operation(
                operation_id,
                status=ProviderOperationStatus.UNKNOWN,
                error_code=exc.code,
            )
            uncertain_refund = await self._refund_repo.get_by_id_for_update(refund_id)
            if uncertain_refund is not None:
                uncertain_refund.status = RefundStatus.UNKNOWN
                uncertain_refund.funds_reserved = True
                uncertain_refund.claim_token = None
                uncertain_refund.claimed_until = None
                await self._session.commit()
            raise PaymentProviderResultUnknown from exc
        except PaymentProviderRejected as exc:
            await self._finish_provider_operation(
                operation_id,
                status=ProviderOperationStatus.FAILED,
                error_code=exc.code,
            )
            rejected_refund = await self._refund_repo.get_by_id_for_update(refund_id)
            if rejected_refund is not None:
                rejected_refund.status = RefundStatus.QUARANTINED
                rejected_refund.funds_reserved = False
                rejected_refund.cancellation_reason = exc.code
                rejected_refund.claim_token = None
                rejected_refund.claimed_until = None
                await self._session.commit()
            raise

        payment = await self._payment_repo.get_by_id_for_update(payment_id)
        result_refund = await self._refund_repo.get_by_id_for_update(refund_id)
        result_operation = await self._operation_repo.get_by_id_for_update(operation_id)
        if payment is None or result_refund is None or result_operation is None:
            raise PaymentVerificationFailed("Refund result target was not found")
        try:
            self._verify_refund(payment, remote_refund, expected_amount=result_refund.amount)
        except PaymentVerificationFailed:
            # The provider returned a refund object after POST, so the balance
            # remains reserved even when its identity or amount is inconsistent.
            result_operation.status = ProviderOperationStatus.QUARANTINED
            result_operation.external_id = remote_refund.id
            result_operation.last_error_code = "provider_verification_failed"
            result_operation.response_payload = self._provider_refund_snapshot(remote_refund)
            result_operation.next_attempt_at = None
            result_operation.claim_token = None
            result_operation.claimed_until = None
            result_refund.status = RefundStatus.QUARANTINED
            result_refund.funds_reserved = True
            result_refund.external_status = remote_refund.status
            result_refund.cancellation_reason = "provider_verification_failed"
            result_refund.next_attempt_at = None
            result_refund.claim_token = None
            result_refund.claimed_until = None
            await self._session.commit()
            raise
        await self._finish_refund(payment, result_refund, remote_refund)
        result_operation.status = ProviderOperationStatus.SUCCEEDED
        result_operation.external_id = remote_refund.id
        result_operation.response_payload = self._provider_refund_snapshot(remote_refund)
        result_operation.claimed_until = None
        await self._session.commit()
        await self._session.refresh(payment)
        return payment

    async def reconcile_refunds(self, *, limit: int = 20) -> int:
        """Recover a bounded batch of new, unknown, pending, or retryable refunds."""
        claim_token, claimed = await self._refund_repo.claim_due(limit=limit)
        refund_ids = [refund.id for refund in claimed]
        await self._session.commit()
        for refund_id in refund_ids:
            await self._reconcile_refund_item(refund_id, claim_token)
        return len(refund_ids)

    async def _reconcile_refund_item(
        self,
        refund_id: uuid.UUID,
        claim_token: uuid.UUID,
    ) -> None:
        refund = await self._refund_repo.get_by_id_for_update(refund_id)
        if refund is None or refund.claim_token != claim_token:
            await self._session.rollback()
            return
        status = refund.status
        payment_id = refund.payment_id
        amount = refund.amount
        reason = refund.reason
        cancellation_reason = refund.cancellation_reason
        external_id = refund.external_id
        operation = await self._operation_repo.get_by_type_and_entity(
            "create_refund", refund.id, for_update=True
        )
        operation_id = operation.id if operation is not None else None
        first_requested_at = (
            operation.first_requested_at or operation.created_at
            if operation is not None
            else refund.created_at
        )
        if first_requested_at.tzinfo is None:
            first_requested_at = first_requested_at.replace(tzinfo=UTC)
        await self._session.commit()

        if status == RefundStatus.CANCELED and cancellation_reason == "rejected_by_timeout":
            attempts = await self._refund_repo.count_by_reason(payment_id, reason)
            if attempts >= 3:
                refund = await self._refund_repo.get_by_id_for_update(refund_id)
                if refund is not None:
                    refund.status = RefundStatus.QUARANTINED
                    refund.funds_reserved = False
                    refund.next_attempt_at = None
                    refund.claim_token = None
                    refund.claimed_until = None
                    await self._session.commit()
                return
            original = await self._refund_repo.get_by_id_for_update(refund_id)
            if original is not None:
                original.cancellation_reason = "rejected_by_timeout_retried"
                original.next_attempt_at = None
                original.claim_token = None
                original.claimed_until = None
                await self._session.commit()
            try:
                await self.refund_payment(
                    payment_id,
                    reason=reason,
                    amount=amount,
                    request_id=f"retry-{refund_id}-{attempts + 1}",
                )
            except PaymentProviderUnavailable:
                return
            return

        if operation_id is None:
            refund = await self._refund_repo.get_by_id_for_update(refund_id)
            if refund is not None:
                refund.status = RefundStatus.QUARANTINED
                refund.funds_reserved = True
                refund.cancellation_reason = "provider_operation_missing"
                refund.claim_token = None
                refund.claimed_until = None
                await self._session.commit()
            return

        if status == RefundStatus.NEW:
            try:
                await self._submit_refund(refund_id, operation_id)
            except PaymentProviderUnavailable:
                return
            return

        if status == RefundStatus.PENDING and external_id is not None:
            try:
                await self.reconcile_refund(external_id)
            except PaymentProviderUnavailable as exc:
                await self._reschedule_refund(refund_id, claim_token, exc.code)
            return

        if status == RefundStatus.UNKNOWN:
            try:
                matched = (
                    await self._provider.get_refund(external_id)
                    if external_id is not None
                    else await self._find_provider_refund(
                        payment_id,
                        amount=amount,
                        first_requested_at=first_requested_at,
                    )
                )
                if matched is not None:
                    local = await self._refund_repo.get_by_id_for_update(refund_id)
                    if local is not None:
                        local.external_id = matched.id
                        local.external_status = matched.status
                        await self._session.commit()
                    await self.reconcile_refund(matched.id)
                    return
            except PaymentProviderUnavailable as exc:
                await self._reschedule_refund(refund_id, claim_token, exc.code)
                return
            except PaymentVerificationFailed:
                local = await self._refund_repo.get_by_id_for_update(refund_id)
                if local is not None:
                    local.status = RefundStatus.QUARANTINED
                    local.funds_reserved = True
                    local.cancellation_reason = "ambiguous_or_mismatched_refund"
                    local.next_attempt_at = None
                    local.claim_token = None
                    local.claimed_until = None
                    await self._session.commit()
                return
            if utc_now() - first_requested_at >= timedelta(hours=24):
                local = await self._refund_repo.get_by_id_for_update(refund_id)
                if local is not None:
                    local.status = RefundStatus.QUARANTINED
                    local.funds_reserved = True
                    local.cancellation_reason = "idempotency_expired:refund_not_found"
                    local.claim_token = None
                    local.claimed_until = None
                    await self._session.commit()
                return
            await self._reschedule_refund(refund_id, claim_token, "provider_refund_not_found")

    async def _find_provider_refund(
        self,
        payment_id: uuid.UUID,
        *,
        amount: int,
        first_requested_at: datetime,
    ) -> ProviderRefund | None:
        payment = await self._payment_repo.get_by_id(payment_id)
        if payment is None or payment.external_id is None:
            raise PaymentVerificationFailed("Refund payment was not found")
        provider_payment_id = payment.external_id
        await self._session.rollback()
        cursor: str | None = None
        matches: list[ProviderRefund] = []
        for _ in range(5):
            page = await self._provider.list_refunds(
                created_gte=first_requested_at - timedelta(minutes=5),
                created_lte=first_requested_at + timedelta(minutes=5),
                payment_id=provider_payment_id,
                limit=100,
                cursor=cursor,
            )
            matches.extend(
                item
                for item in page.items
                if item.payment_id == provider_payment_id and item.amount == amount
            )
            if len(matches) > 1 or page.next_cursor is None:
                break
            cursor = page.next_cursor
        if len(matches) > 1:
            raise PaymentVerificationFailed("Multiple provider refunds matched one operation")
        return matches[0] if matches else None

    async def _reschedule_refund(
        self,
        refund_id: uuid.UUID,
        claim_token: uuid.UUID,
        error_code: str,
    ) -> None:
        refund = await self._refund_repo.get_by_id_for_update(refund_id)
        if refund is None or refund.claim_token != claim_token:
            await self._session.rollback()
            return
        ceiling = min(30 * (2 ** min(refund.attempt_count, 5)), 900)
        refund.next_attempt_at = utc_now() + timedelta(
            seconds=random.uniform(ceiling / 2, ceiling)  # noqa: S311
        )
        refund.cancellation_reason = error_code
        refund.claim_token = None
        refund.claimed_until = None
        await self._session.commit()

    async def reconcile_refund(self, external_id: str) -> PaymentModel:
        """Apply a verified asynchronous refund status."""
        refund = await self._provider.get_refund(external_id)
        if refund.id != external_id:
            raise PaymentVerificationFailed("Provider refund identifier does not match")
        payment = await self._payment_repo.get_by_external_id_for_update(refund.payment_id)
        if payment is None:
            raise PaymentVerificationFailed("Refunded payment was not found")
        local_refund = await self._refund_repo.get_by_external_id_for_update(refund.id)
        if local_refund is None:
            raise PaymentVerificationFailed("Local refund was not found")
        self._verify_refund(payment, refund, expected_amount=local_refund.amount)
        await self._finish_refund(payment, local_refund, refund)
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
