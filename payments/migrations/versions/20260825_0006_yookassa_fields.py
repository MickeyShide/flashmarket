"""Add YooKassa provider fields.

Revision ID: 20260825_0006
Revises: 20260819_0005
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0006"
down_revision: str | Sequence[str] | None = "20260819_0005"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("external_status", sa.String(64), nullable=True))
    op.add_column("payments", sa.Column("confirmation_url", sa.String(2048), nullable=True))
    op.add_column("payments", sa.Column("cancellation_reason", sa.String(255), nullable=True))
    op.add_column("payments", sa.Column("provider_test", sa.Boolean(), nullable=True))
    op.add_column("payments", sa.Column("refund_external_id", sa.String(255), nullable=True))
    op.add_column("payments", sa.Column("refund_status", sa.String(64), nullable=True))
    op.create_index(
        "uq_payments_external_id",
        "payments",
        ["external_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_payments_external_id", table_name="payments")
    op.drop_column("payments", "refund_status")
    op.drop_column("payments", "refund_external_id")
    op.drop_column("payments", "provider_test")
    op.drop_column("payments", "cancellation_reason")
    op.drop_column("payments", "confirmation_url")
    op.drop_column("payments", "external_status")
