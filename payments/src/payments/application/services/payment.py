"""Payment application service."""

from __future__ import annotations

import json
import uuid
from datetime import UTC

from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.schemas import CreatePaymentRequest
from payments.domain.entities import PaymentEventType, PaymentStatus
from payments.domain.exceptions import InvalidPaymentState, PaymentNotFound
from payments.infrastructure.database import utc_now
from payments.infrastructure.models import PaymentModel
from payments.infrastructure.repositories.payment import OutboxRepository, PaymentRepository


class PaymentService:
    """Orchestrates payment lifecycle."""

    def __init__(
        self,
        session: AsyncSession,
        payment_repo: PaymentRepository,
        outbox_repo: OutboxRepository,
    ) -> None:
        self._session = session
        self._payment_repo = payment_repo
        self._outbox_repo = outbox_repo

    async def create_payment(self, data: CreatePaymentRequest) -> PaymentModel:
        """Create a pending payment for an order."""
        existing = await self._payment_repo.get_by_order_id(data.order_id)
        if existing is not None and existing.status == PaymentStatus.PENDING:
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
        await self._payment_repo.create(payment)
        await self._session.commit()
        await self._session.refresh(payment)
        return payment

    async def confirm_payment(self, payment_id: uuid.UUID) -> PaymentModel:
        """Mark a pending payment as successful and emit an event."""
        payment = await self._payment_repo.get_by_id_for_update(payment_id)
        if payment is None:
            raise PaymentNotFound
        if payment.status != PaymentStatus.PENDING:
            raise InvalidPaymentState("Payment is not pending")
        expires_at = payment.expires_at
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if utc_now() >= expires_at:
                raise InvalidPaymentState("Payment deadline has expired")

        payment.status = PaymentStatus.SUCCESS
        payment.external_id = uuid.uuid7().hex
        await self._payment_repo.update(payment)

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

        await self._session.commit()
        await self._session.refresh(payment)
        return payment

    async def fail_payment(self, payment_id: uuid.UUID) -> PaymentModel:
        """Mark a pending payment as failed and emit an event."""
        payment = await self._payment_repo.get_by_id_for_update(payment_id)
        if payment is None:
            raise PaymentNotFound
        if payment.status != PaymentStatus.PENDING:
            raise InvalidPaymentState("Payment is not pending")

        payment.status = PaymentStatus.FAILED
        await self._payment_repo.update(payment)

        payload = {
            "payment_id": str(payment.id),
            "order_id": str(payment.order_id),
            "user_id": str(payment.user_id),
            "amount": payment.amount,
            "currency": payment.currency,
            "reason": "provider_declined",
        }
        await self._outbox_repo.add(
            PaymentEventType.PAYMENT_FAILED,
            json.dumps(payload, separators=(",", ":")),
        )

        await self._session.commit()
        await self._session.refresh(payment)
        return payment

    async def cancel_payment(self, payment_id: uuid.UUID) -> PaymentModel:
        """Cancel a pending payment and emit an event."""
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
