"""Add foreign key constraints for receipts, daily report lines, and financial ledger.

Revision ID: 20260826_0016
Revises: 20260825_0015
Create Date: 2026-08-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260826_0016"
down_revision: str | Sequence[str] | None = "20260825_0015"
branch_labels = depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("payment_receipts") as batch_op:
        batch_op.create_foreign_key(
            "fk_payment_receipts_payment_id",
            "payments",
            ["payment_id"],
            ["id"],
            ondelete="CASCADE",
        )
    with op.batch_alter_table("daily_report_lines") as batch_op:
        batch_op.create_foreign_key(
            "fk_daily_report_lines_report_id",
            "daily_report_imports",
            ["report_id"],
            ["id"],
            ondelete="CASCADE",
        )
    with op.batch_alter_table("financial_ledger") as batch_op:
        batch_op.create_foreign_key(
            "fk_financial_ledger_payment_id",
            "payments",
            ["payment_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("financial_ledger") as batch_op:
        batch_op.drop_constraint("fk_financial_ledger_payment_id", type_="foreignkey")
    with op.batch_alter_table("daily_report_lines") as batch_op:
        batch_op.drop_constraint("fk_daily_report_lines_report_id", type_="foreignkey")
    with op.batch_alter_table("payment_receipts") as batch_op:
        batch_op.drop_constraint("fk_payment_receipts_payment_id", type_="foreignkey")
