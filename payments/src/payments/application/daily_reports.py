"""Deterministic YooKassa daily CSV reconciliation against the local ledger."""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from payments.domain.entities import ReportImportStatus
from payments.infrastructure.models import DailyReportImportModel, DailyReportLineModel
from payments.infrastructure.repositories.payment import (
    DailyReportRepository,
    FinancialLedgerRepository,
)
from payments.observability import REPORT_DISCREPANCIES, REPORT_IMPORTS

MOSCOW = ZoneInfo("Europe/Moscow")

_ALIASES = {
    "payment_id": (
        "Идентификатор платежа",
        "Идентификатор платежа ЮKassa",
        "payment_id",
    ),
    "refund_id": (
        "Идентификатор возврата",
        "Идентификатор возврата ЮKassa",
        "refund_id",
    ),
    "amount": ("Сумма платежа", "Сумма возврата", "amount"),
    "currency": ("Валюта платежа", "Валюта возврата", "currency"),
    "occurred_at": ("Время платежа", "Время возврата", "occurred_at"),
}


class InvalidDailyReport(ValueError):
    """The CSV cannot be safely interpreted using a supported YooKassa schema."""


def _value(row: dict[str, str], key: str) -> str | None:
    for alias in _ALIASES[key]:
        value = row.get(alias)
        if value:
            return value.strip()
    return None


def _kopecks(raw: str) -> int:
    try:
        amount = Decimal(raw.replace(" ", "").replace(",", ".")) * 100
    except InvalidOperation as exc:
        raise InvalidDailyReport("invalid report amount") from exc
    if amount <= 0 or amount != amount.to_integral_value():
        raise InvalidDailyReport("report amount must be positive with at most two decimals")
    return int(amount)


def _timestamp(raw: str) -> datetime:
    try:
        parsed = datetime.strptime(raw, "%d.%m.%Y %H:%M:%S")
    except ValueError:
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError as exc:
            raise InvalidDailyReport("invalid report timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=MOSCOW)
    return parsed.astimezone(MOSCOW)


async def import_daily_report(
    session: AsyncSession,
    content: bytes,
    *,
    report_type: str,
) -> DailyReportImportModel:
    """Import once, quarantine discrepancies, and never alter payment state."""
    if report_type not in {"payment", "refund"}:
        raise InvalidDailyReport("report_type must be payment or refund")
    content_hash = sha256(content).hexdigest()
    reports = DailyReportRepository(session)
    existing = await reports.get_by_content_hash(content_hash)
    if existing is not None:
        REPORT_IMPORTS.labels(result="duplicate").inc()
        return existing
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InvalidDailyReport("report must be UTF-8") from exc
    rows = list(csv.DictReader(io.StringIO(decoded), delimiter=";"))
    if not rows:
        raise InvalidDailyReport("report has no data rows")

    ledger = FinancialLedgerRepository(session)
    parsed: list[tuple[int, str, int, str, datetime, str, str | None]] = []
    entry_type = "PAYMENT_CAPTURE" if report_type == "payment" else "REFUND"
    id_key = "payment_id" if report_type == "payment" else "refund_id"
    total_amount = 0
    for line_number, row in enumerate(rows, start=2):
        provider_id = _value(row, id_key)
        raw_amount = _value(row, "amount")
        currency = _value(row, "currency")
        raw_time = _value(row, "occurred_at")
        if not provider_id or not raw_amount or not currency or not raw_time:
            raise InvalidDailyReport(f"required field missing on line {line_number}")
        amount = _kopecks(raw_amount)
        occurred_at = _timestamp(raw_time)
        local = await ledger.get_by_provider_object(entry_type, provider_id)
        error: str | None = None
        if local is None:
            error = "ledger_entry_missing"
        elif local.amount != amount:
            error = "amount_mismatch"
        elif local.currency != currency:
            error = "currency_mismatch"
        parsed.append(
            (
                line_number,
                provider_id,
                amount,
                currency,
                occurred_at,
                "MATCHED" if error is None else "QUARANTINED",
                error,
            )
        )
        total_amount += amount

    discrepancy_count = sum(1 for *_, error in parsed if error is not None)
    business_dates = {item[4].date() for item in parsed}
    if len(business_dates) != 1:
        raise InvalidDailyReport("daily report contains multiple Moscow business dates")
    report = DailyReportImportModel(
        id=uuid.uuid7(),
        content_hash=content_hash,
        report_type=report_type,
        business_date=business_dates.pop(),
        status=(
            ReportImportStatus.DISCREPANCIES if discrepancy_count else ReportImportStatus.MATCHED
        ),
        total_rows=len(parsed),
        total_amount=total_amount,
        discrepancy_count=discrepancy_count,
    )
    lines = [
        DailyReportLineModel(
            id=uuid.uuid7(),
            report_id=report.id,
            line_number=line_number,
            provider_object_id=provider_id,
            operation_type=report_type,
            amount=amount,
            currency=currency,
            occurred_at=occurred_at,
            match_status=match_status,
            error_code=error,
        )
        for line_number, provider_id, amount, currency, occurred_at, match_status, error in parsed
    ]
    try:
        await reports.create(report, lines)
        await session.commit()
    except IntegrityError:
        await session.rollback()
        concurrent = await reports.get_by_content_hash(content_hash)
        if concurrent is None:
            raise
        REPORT_IMPORTS.labels(result="duplicate").inc()
        return concurrent
    await session.refresh(report)
    REPORT_IMPORTS.labels(result="discrepancies" if discrepancy_count else "matched").inc()
    if discrepancy_count:
        REPORT_DISCREPANCIES.inc(discrepancy_count)
    return report
