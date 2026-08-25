"""Add append-only ledger, receipt snapshots, and daily report imports.

Revision ID: 20260825_0012
Revises: 20260825_0011
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0012"
down_revision: str | Sequence[str] | None = "20260825_0011"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "financial_ledger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("refund_id", sa.Uuid(), nullable=True),
        sa.Column("entry_type", sa.String(32), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("provider_object_id", sa.String(255), nullable=False),
        sa.Column("event_key", sa.String(320), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_financial_ledger_amount_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_key", name="uq_financial_ledger_event_key"),
    )
    op.create_index("ix_financial_ledger_payment_id", "financial_ledger", ["payment_id"])
    op.create_index("ix_financial_ledger_refund_id", "financial_ledger", ["refund_id"])
    op.create_index(
        "ix_financial_ledger_provider_object",
        "financial_ledger",
        ["entry_type", "provider_object_id"],
    )
    op.create_table(
        "payment_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_id", name="uq_payment_receipts_payment_id"),
    )
    op.create_index("ix_payment_receipts_payment_id", "payment_receipts", ["payment_id"])
    op.create_table(
        "daily_report_imports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("report_type", sa.String(16), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False),
        sa.Column("total_amount", sa.Integer(), nullable=False),
        sa.Column("discrepancy_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash", name="uq_daily_reports_content_hash"),
    )
    op.create_index(
        "ix_daily_report_imports_business_date", "daily_report_imports", ["business_date"]
    )
    op.create_table(
        "daily_report_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("provider_object_id", sa.String(255), nullable=False),
        sa.Column("operation_type", sa.String(16), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("match_status", sa.String(20), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("report_id", "line_number", name="uq_daily_report_line_number"),
    )
    op.create_index("ix_daily_report_lines_report_id", "daily_report_lines", ["report_id"])
    op.create_index(
        "ix_daily_report_lines_provider_object_id",
        "daily_report_lines",
        ["provider_object_id"],
    )


def downgrade() -> None:
    op.drop_table("daily_report_lines")
    op.drop_table("daily_report_imports")
    op.drop_table("payment_receipts")
    op.drop_table("financial_ledger")
