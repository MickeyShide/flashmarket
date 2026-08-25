"""Add leased reconciliation state to payment attempts.

Revision ID: 20260825_0013
Revises: 20260825_0012
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0013"
down_revision: str | Sequence[str] | None = "20260825_0012"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column(
        "payment_attempts",
        sa.Column("reconcile_attempt_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("payment_attempts", sa.Column("next_reconcile_at", sa.DateTime(timezone=True)))
    op.add_column("payment_attempts", sa.Column("claim_token", sa.Uuid()))
    op.add_column("payment_attempts", sa.Column("claimed_until", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_payment_attempts_reconcile",
        "payment_attempts",
        ["status", "next_reconcile_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_payment_attempts_reconcile", table_name="payment_attempts")
    op.drop_column("payment_attempts", "claimed_until")
    op.drop_column("payment_attempts", "claim_token")
    op.drop_column("payment_attempts", "next_reconcile_at")
    op.drop_column("payment_attempts", "reconcile_attempt_count")
