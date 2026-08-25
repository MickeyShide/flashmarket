"""Separate refund balance reservations from workflow status.

Revision ID: 20260825_0014
Revises: 20260825_0013
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0014"
down_revision: str | Sequence[str] | None = "20260825_0013"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column(
        "refunds",
        sa.Column("funds_reserved", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_index(
        "ix_refunds_reserved_balance",
        "refunds",
        ["payment_id", "funds_reserved"],
    )

    refunds = sa.table(
        "refunds",
        sa.column("status", sa.String()),
        sa.column("cancellation_reason", sa.String()),
        sa.column("funds_reserved", sa.Boolean()),
    )
    reason = sa.func.coalesce(refunds.c.cancellation_reason, "")
    ambiguous_quarantine = sa.or_(
        reason.like("idempotency_expired:%"),
        reason.in_(
            (
                "provider_operation_missing",
                "provider_verification_failed",
                "ambiguous_or_mismatched_refund",
            )
        ),
    )
    op.get_bind().execute(
        refunds.update()
        .where(
            sa.or_(
                refunds.c.status == "CANCELED",
                sa.and_(refunds.c.status == "QUARANTINED", sa.not_(ambiguous_quarantine)),
            )
        )
        .values(funds_reserved=False)
    )


def downgrade() -> None:
    op.drop_index("ix_refunds_reserved_balance", table_name="refunds")
    op.drop_column("refunds", "funds_reserved")
