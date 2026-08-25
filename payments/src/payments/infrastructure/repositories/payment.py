"""Payment and outbox persistence operations."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import timedelta
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from payments.domain.entities import (
    PaymentAttemptStatus,
    ProviderOperationStatus,
    RefundStatus,
    WebhookInboxStatus,
)
from payments.infrastructure.database import utc_now
from payments.infrastructure.models import (
    DailyReportImportModel,
    DailyReportLineModel,
    FinancialLedgerModel,
    OutboxEventModel,
    PaymentAttemptModel,
    PaymentModel,
    PaymentReceiptModel,
    ProviderOperationModel,
    RefundModel,
    WebhookInboxModel,
)


class FinancialLedgerRepository:
    """Idempotent posting and read-only reconciliation for accounting facts."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def post(self, entry: FinancialLedgerModel) -> FinancialLedgerModel:
        existing = await self.get_by_event_key(entry.event_key)
        if existing is not None:
            return existing
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_by_event_key(self, event_key: str) -> FinancialLedgerModel | None:
        result = await self._session.scalars(
            select(FinancialLedgerModel).where(FinancialLedgerModel.event_key == event_key)
        )
        return result.first()

    async def get_by_provider_object(
        self, entry_type: str, provider_object_id: str
    ) -> FinancialLedgerModel | None:
        result = await self._session.scalars(
            select(FinancialLedgerModel).where(
                FinancialLedgerModel.entry_type == entry_type,
                FinancialLedgerModel.provider_object_id == provider_object_id,
            )
        )
        return result.first()


class PaymentReceiptRepository:
    """Persistence for one immutable receipt snapshot per payment."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, receipt: PaymentReceiptModel) -> PaymentReceiptModel:
        existing = await self.get_by_payment_id(receipt.payment_id)
        if existing is not None:
            return existing
        self._session.add(receipt)
        await self._session.flush()
        return receipt

    async def get_by_payment_id(self, payment_id: UUID) -> PaymentReceiptModel | None:
        result = await self._session.scalars(
            select(PaymentReceiptModel).where(PaymentReceiptModel.payment_id == payment_id)
        )
        return result.first()


class DailyReportRepository:
    """Persistence for idempotent, non-mutating daily report imports."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_content_hash(self, content_hash: str) -> DailyReportImportModel | None:
        result = await self._session.scalars(
            select(DailyReportImportModel).where(
                DailyReportImportModel.content_hash == content_hash
            )
        )
        return result.first()

    async def create(
        self,
        report: DailyReportImportModel,
        lines: Sequence[DailyReportLineModel],
    ) -> DailyReportImportModel:
        self._session.add(report)
        self._session.add_all(lines)
        await self._session.flush()
        return report


class PaymentRepository:
    """Data-access layer for payments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payment: PaymentModel) -> PaymentModel:
        """Persist a new payment."""
        self._session.add(payment)
        await self._session.flush()
        return payment

    async def get_by_id(self, payment_id: UUID) -> PaymentModel | None:
        """Fetch a payment by primary key."""
        return await self._session.get(PaymentModel, payment_id)

    async def get_by_id_for_update(self, payment_id: UUID) -> PaymentModel | None:
        """Fetch a payment by primary key with an exclusive row lock."""
        result = await self._session.scalars(
            select(PaymentModel)
            .where(PaymentModel.id == payment_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.first()

    async def get_by_order_id(self, order_id: UUID) -> PaymentModel | None:
        """Fetch the most recent payment for an order."""
        result = await self._session.scalars(
            select(PaymentModel)
            .where(PaymentModel.order_id == order_id)
            .order_by(PaymentModel.created_at.desc())
        )
        return result.first()

    async def get_by_external_id(self, external_id: str) -> PaymentModel | None:
        """Fetch a payment by provider identifier."""
        result = await self._session.scalars(
            select(PaymentModel).where(PaymentModel.external_id == external_id)
        )
        return result.first()

    async def get_by_external_id_for_update(self, external_id: str) -> PaymentModel | None:
        """Fetch a provider payment with an exclusive row lock."""
        result = await self._session.scalars(
            select(PaymentModel)
            .where(PaymentModel.external_id == external_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.first()

    async def get_by_order_id_for_update(self, order_id: UUID) -> PaymentModel | None:
        """Fetch the payment for an order with an exclusive row lock."""
        result = await self._session.scalars(
            select(PaymentModel)
            .where(PaymentModel.order_id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.first()

    async def count_by_user(self, user_id: UUID) -> int:
        """Return the total number of payments for a user."""
        result = await self._session.scalar(
            select(func.count(PaymentModel.id)).where(PaymentModel.user_id == user_id)
        )
        return result or 0

    async def list_by_user(
        self,
        user_id: UUID,
        *,
        limit: int,
        offset: int,
    ) -> Sequence[PaymentModel]:
        """Return a user's payments ordered by creation time."""
        result = await self._session.scalars(
            select(PaymentModel)
            .where(PaymentModel.user_id == user_id)
            .order_by(PaymentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return result.all()

    async def update(self, payment: PaymentModel) -> PaymentModel:
        """Flush pending attribute changes on a payment."""
        await self._session.flush()
        return payment


class PaymentAttemptRepository:
    """Persistence for concrete provider checkout attempts."""

    ACTIVE_STATUSES = (
        PaymentAttemptStatus.NEW,
        PaymentAttemptStatus.PREPARING,
        PaymentAttemptStatus.UNKNOWN,
        PaymentAttemptStatus.PENDING,
    )

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, attempt: PaymentAttemptModel) -> PaymentAttemptModel:
        self._session.add(attempt)
        await self._session.flush()
        return attempt

    async def get_by_id_for_update(self, attempt_id: UUID) -> PaymentAttemptModel | None:
        result = await self._session.scalars(
            select(PaymentAttemptModel)
            .where(PaymentAttemptModel.id == attempt_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.first()

    async def get_active_for_update(self, payment_id: UUID) -> PaymentAttemptModel | None:
        result = await self._session.scalars(
            select(PaymentAttemptModel)
            .where(
                PaymentAttemptModel.payment_id == payment_id,
                PaymentAttemptModel.status.in_(self.ACTIVE_STATUSES),
            )
            .order_by(PaymentAttemptModel.attempt_number.desc())
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.first()

    async def get_by_external_id_for_update(self, external_id: str) -> PaymentAttemptModel | None:
        result = await self._session.scalars(
            select(PaymentAttemptModel)
            .where(PaymentAttemptModel.external_id == external_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.first()

    async def next_attempt_number(self, payment_id: UUID) -> int:
        current = await self._session.scalar(
            select(func.max(PaymentAttemptModel.attempt_number)).where(
                PaymentAttemptModel.payment_id == payment_id
            )
        )
        return int(current or 0) + 1

    async def claim_due(
        self,
        *,
        limit: int,
        lease_seconds: int = 60,
    ) -> tuple[UUID, Sequence[PaymentAttemptModel]]:
        """Claim active attempts that already have a safe provider GET identity."""
        now = utc_now()
        token = uuid.uuid4()
        result = await self._session.scalars(
            select(PaymentAttemptModel)
            .where(
                PaymentAttemptModel.status.in_(
                    [
                        PaymentAttemptStatus.PREPARING,
                        PaymentAttemptStatus.UNKNOWN,
                        PaymentAttemptStatus.PENDING,
                    ]
                ),
                PaymentAttemptModel.external_id.is_not(None),
                or_(
                    PaymentAttemptModel.next_reconcile_at.is_(None),
                    PaymentAttemptModel.next_reconcile_at <= now,
                ),
                or_(
                    PaymentAttemptModel.claimed_until.is_(None),
                    PaymentAttemptModel.claimed_until <= now,
                ),
            )
            .order_by(PaymentAttemptModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        attempts = result.all()
        for attempt in attempts:
            attempt.claim_token = token
            attempt.claimed_until = now + timedelta(seconds=lease_seconds)
            attempt.reconcile_attempt_count += 1
        await self._session.flush()
        return token, attempts


class RefundRepository:
    """Persistence and balance queries for normalized refunds."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, refund: RefundModel) -> RefundModel:
        self._session.add(refund)
        await self._session.flush()
        return refund

    async def get_by_id(self, refund_id: UUID) -> RefundModel | None:
        return await self._session.get(RefundModel, refund_id)

    async def get_by_request_key(self, request_key: str) -> RefundModel | None:
        result = await self._session.scalars(
            select(RefundModel).where(RefundModel.request_key == request_key)
        )
        return result.first()

    async def get_latest_by_reason(
        self,
        payment_id: UUID,
        reason: str,
    ) -> RefundModel | None:
        result = await self._session.scalars(
            select(RefundModel)
            .where(RefundModel.payment_id == payment_id, RefundModel.reason == reason)
            .order_by(RefundModel.created_at.desc())
        )
        return result.first()

    async def count_by_reason(self, payment_id: UUID, reason: str) -> int:
        value = await self._session.scalar(
            select(func.count(RefundModel.id)).where(
                RefundModel.payment_id == payment_id,
                RefundModel.reason == reason,
            )
        )
        return int(value or 0)

    async def get_by_id_for_update(self, refund_id: UUID) -> RefundModel | None:
        result = await self._session.scalars(
            select(RefundModel)
            .where(RefundModel.id == refund_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.first()

    async def get_by_external_id_for_update(self, external_id: str) -> RefundModel | None:
        result = await self._session.scalars(
            select(RefundModel)
            .where(RefundModel.external_id == external_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.first()

    async def reserved_amount(self, payment_id: UUID) -> int:
        value = await self._session.scalar(
            select(func.coalesce(func.sum(RefundModel.amount), 0)).where(
                RefundModel.payment_id == payment_id,
                RefundModel.funds_reserved.is_(True),
            )
        )
        return int(value or 0)

    async def succeeded_amount(self, payment_id: UUID) -> int:
        value = await self._session.scalar(
            select(func.coalesce(func.sum(RefundModel.amount), 0)).where(
                RefundModel.payment_id == payment_id,
                RefundModel.status == RefundStatus.SUCCEEDED,
            )
        )
        return int(value or 0)

    async def claim_due(
        self,
        *,
        limit: int,
        lease_seconds: int = 60,
    ) -> tuple[UUID, Sequence[RefundModel]]:
        now = utc_now()
        token = uuid.uuid4()
        result = await self._session.scalars(
            select(RefundModel)
            .where(
                or_(
                    RefundModel.status.in_(
                        [RefundStatus.NEW, RefundStatus.UNKNOWN, RefundStatus.PENDING]
                    ),
                    and_(
                        RefundModel.status == RefundStatus.CANCELED,
                        RefundModel.cancellation_reason == "rejected_by_timeout",
                    ),
                ),
                or_(RefundModel.next_attempt_at.is_(None), RefundModel.next_attempt_at <= now),
                or_(RefundModel.claimed_until.is_(None), RefundModel.claimed_until <= now),
            )
            .order_by(RefundModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        refunds = result.all()
        for refund in refunds:
            refund.claim_token = token
            refund.claimed_until = now + timedelta(seconds=lease_seconds)
        await self._session.flush()
        return token, refunds


class ProviderOperationRepository:
    """Persistence for idempotent provider write operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, operation: ProviderOperationModel) -> ProviderOperationModel:
        self._session.add(operation)
        await self._session.flush()
        return operation

    async def get_by_type_and_entity(
        self,
        operation_type: str,
        entity_id: UUID,
        *,
        for_update: bool = False,
    ) -> ProviderOperationModel | None:
        query = select(ProviderOperationModel).where(
            ProviderOperationModel.operation_type == operation_type,
            ProviderOperationModel.entity_id == entity_id,
        )
        if for_update:
            query = query.with_for_update().execution_options(populate_existing=True)
        result = await self._session.scalars(query)
        return result.first()

    async def get_by_id_for_update(self, operation_id: UUID) -> ProviderOperationModel | None:
        result = await self._session.scalars(
            select(ProviderOperationModel)
            .where(ProviderOperationModel.id == operation_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.first()

    async def claim_due_unknown(
        self,
        *,
        limit: int,
        lease_seconds: int = 60,
    ) -> tuple[UUID, Sequence[ProviderOperationModel]]:
        now = utc_now()
        claim_token = uuid.uuid4()
        result = await self._session.scalars(
            select(ProviderOperationModel)
            .where(
                ProviderOperationModel.operation_type == "create_payment",
                or_(
                    ProviderOperationModel.status == ProviderOperationStatus.UNKNOWN,
                    and_(
                        ProviderOperationModel.status == ProviderOperationStatus.IN_FLIGHT,
                        ProviderOperationModel.claimed_until <= now,
                    ),
                ),
                or_(
                    ProviderOperationModel.next_attempt_at.is_(None),
                    ProviderOperationModel.next_attempt_at <= now,
                ),
                (
                    (ProviderOperationModel.claimed_until.is_(None))
                    | (ProviderOperationModel.claimed_until <= now)
                ),
            )
            .order_by(ProviderOperationModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        operations = result.all()
        for operation in operations:
            operation.claim_token = claim_token
            operation.claimed_until = now + timedelta(seconds=lease_seconds)
        await self._session.flush()
        return claim_token, operations

    async def update(self, operation: ProviderOperationModel) -> ProviderOperationModel:
        await self._session.flush()
        return operation


class WebhookInboxRepository:
    """Persistence and leased batch claims for provider notifications."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, item: WebhookInboxModel) -> WebhookInboxModel:
        self._session.add(item)
        await self._session.flush()
        return item

    async def get_by_dedupe_hash(self, dedupe_hash: str) -> WebhookInboxModel | None:
        result = await self._session.scalars(
            select(WebhookInboxModel).where(WebhookInboxModel.dedupe_hash == dedupe_hash)
        )
        return result.first()

    async def get_by_id_for_update(self, item_id: UUID) -> WebhookInboxModel | None:
        result = await self._session.scalars(
            select(WebhookInboxModel)
            .where(WebhookInboxModel.id == item_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        return result.first()

    async def claim_due(
        self,
        *,
        limit: int,
        lease_seconds: int = 60,
    ) -> tuple[UUID, Sequence[WebhookInboxModel]]:
        now = utc_now()
        token = uuid.uuid4()
        result = await self._session.scalars(
            select(WebhookInboxModel)
            .where(
                or_(
                    WebhookInboxModel.status.in_(
                        [WebhookInboxStatus.PENDING, WebhookInboxStatus.RETRY]
                    ),
                    (
                        (WebhookInboxModel.status == WebhookInboxStatus.PROCESSING)
                        & (WebhookInboxModel.claimed_until <= now)
                    ),
                ),
                or_(
                    WebhookInboxModel.next_attempt_at.is_(None),
                    WebhookInboxModel.next_attempt_at <= now,
                ),
            )
            .order_by(WebhookInboxModel.received_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        items = result.all()
        for item in items:
            item.status = WebhookInboxStatus.PROCESSING
            item.claim_token = token
            item.claimed_until = now + timedelta(seconds=lease_seconds)
            item.attempt_count += 1
        await self._session.flush()
        return token, items


class OutboxRepository:
    """Transactional outbox persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, event_type: str, payload: str) -> OutboxEventModel:
        """Persist an outbox event within the current transaction."""
        event = OutboxEventModel(event_type=event_type, payload=payload)
        self._session.add(event)
        await self._session.flush()
        return event

    async def list_pending(self, limit: int) -> Sequence[OutboxEventModel]:
        """Return pending outbox events for the relay worker."""
        result = await self._session.scalars(
            select(OutboxEventModel)
            .where(OutboxEventModel.status == "pending")
            .order_by(OutboxEventModel.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return result.all()

    async def mark_published(self, event: OutboxEventModel) -> OutboxEventModel:
        """Mark an outbox event as published."""
        event.status = "published"
        event.published_at = utc_now()
        await self._session.flush()
        return event

    async def mark_failed(self, event: OutboxEventModel) -> OutboxEventModel:
        """Mark an outbox event as failed."""
        event.status = "failed"
        event.published_at = None
        await self._session.flush()
        return event
