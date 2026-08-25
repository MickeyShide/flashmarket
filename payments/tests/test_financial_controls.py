"""Regression tests for ledger, receipt, and daily report controls."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from payments.application.contracts import ProviderPayment
from payments.application.daily_reports import import_daily_report
from payments.application.receipts import ReceiptCustomer, ReceiptItem, ReceiptSnapshot
from payments.application.services.payment import PaymentService
from payments.domain.entities import PaymentStatus, ReportImportStatus
from payments.infrastructure.models import (
    DailyReportLineModel,
    FinancialLedgerModel,
    PaymentModel,
)
from payments.infrastructure.providers.mock import MockPaymentProvider
from payments.infrastructure.repositories.payment import OutboxRepository, PaymentRepository

FIXTURE = Path(__file__).parent / "fixtures" / "yookassa_daily_payments.csv"


def _receipt(*, total: int = 12_990, contact: bool = True) -> ReceiptSnapshot:
    return ReceiptSnapshot(
        total_amount=total,
        items=[
            ReceiptItem(
                description="Test sneakers",
                quantity=Decimal("1"),
                unit_amount=12_990,
                vat_code=1,
                payment_subject="commodity",
                payment_mode="full_payment",
                measure="piece",
            )
        ],
        customer=ReceiptCustomer(email="buyer@example.test") if contact else None,
    )


def test_receipt_contract_is_canonical_and_exact() -> None:
    receipt = _receipt()
    assert receipt.content_hash() == receipt.content_hash()
    assert receipt.items[0].total_kopecks() == 12_990

    with pytest.raises(ValidationError, match="exactly equal"):
        _receipt(total=12_991)
    with pytest.raises(ValidationError, match="email or phone"):
        ReceiptCustomer()
    with pytest.raises(ValidationError):
        ReceiptItem(
            description="Invalid precision",
            quantity=Decimal("0.0001"),
            unit_amount=100,
            vat_code=1,
            payment_subject="commodity",
            payment_mode="full_payment",
            measure="piece",
        )


@pytest.mark.asyncio
async def test_success_transition_posts_ledger_once(db_session: AsyncSession) -> None:
    payment = PaymentModel(
        order_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        amount=12_990,
        currency="RUB",
        provider="mock",
        status=PaymentStatus.PENDING,
    )
    db_session.add(payment)
    await db_session.commit()
    remote = ProviderPayment(
        id="yk-payment-1",
        status="succeeded",
        amount=12_990,
        currency="RUB",
        test=True,
        metadata={"payment_id": str(payment.id), "order_id": str(payment.order_id)},
    )
    service = PaymentService(
        session=db_session,
        payment_repo=PaymentRepository(db_session),
        outbox_repo=OutboxRepository(db_session),
    )

    await service.reconcile_payment(remote)
    await service.reconcile_payment(remote)

    entries = int(await db_session.scalar(select(func.count(FinancialLedgerModel.id))) or 0)
    assert entries == 1
    entry = (await db_session.scalars(select(FinancialLedgerModel))).one()
    assert (entry.entry_type, entry.direction, entry.amount) == (
        "PAYMENT_CAPTURE",
        "CREDIT",
        12_990,
    )


@pytest.mark.asyncio
async def test_successful_refund_posts_atomic_debit(db_session: AsyncSession) -> None:
    payment = PaymentModel(
        order_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        amount=12_990,
        currency="RUB",
        provider="mock",
        status=PaymentStatus.SUCCESS,
        external_id="mock-captured-payment",
        external_status="succeeded",
        provider_test=True,
    )
    db_session.add(payment)
    await db_session.commit()
    service = PaymentService(
        session=db_session,
        payment_repo=PaymentRepository(db_session),
        outbox_repo=OutboxRepository(db_session),
        provider=MockPaymentProvider(),
    )

    await service.refund_payment(payment.id, amount=5_000, request_id="partial-1")

    entry = (
        await db_session.scalars(
            select(FinancialLedgerModel).where(FinancialLedgerModel.entry_type == "REFUND")
        )
    ).one()
    assert (entry.direction, entry.amount, entry.refund_id is not None) == ("DEBIT", 5_000, True)


@pytest.mark.asyncio
async def test_daily_report_import_is_idempotent_and_uses_moscow_date(
    db_session: AsyncSession,
) -> None:
    payment_id = uuid.uuid4()
    db_session.add(
        FinancialLedgerModel(
            payment_id=payment_id,
            entry_type="PAYMENT_CAPTURE",
            direction="CREDIT",
            amount=12_990,
            currency="RUB",
            provider_object_id="yk-payment-1",
            event_key="payment_capture:yk-payment-1",
            occurred_at=datetime(2026, 8, 25, 20, 59, 59, tzinfo=UTC),
        )
    )
    await db_session.commit()
    content = FIXTURE.read_bytes()

    first = await import_daily_report(db_session, content, report_type="payment")
    second = await import_daily_report(db_session, content, report_type="payment")

    assert first.id == second.id
    assert first.business_date.isoformat() == "2026-08-25"
    assert first.status == ReportImportStatus.MATCHED
    assert first.discrepancy_count == 0


@pytest.mark.asyncio
async def test_report_discrepancy_is_quarantined_without_mutating_ledger(
    db_session: AsyncSession,
) -> None:
    content = FIXTURE.read_bytes().replace(b"129.90", b"130.00")
    report = await import_daily_report(db_session, content, report_type="payment")

    assert report.status == ReportImportStatus.DISCREPANCIES
    assert report.discrepancy_count == 1
    line = (await db_session.scalars(select(DailyReportLineModel))).one()
    assert line.match_status == "QUARANTINED"
    assert line.error_code == "ledger_entry_missing"
    assert int(await db_session.scalar(select(func.count(FinancialLedgerModel.id))) or 0) == 0
