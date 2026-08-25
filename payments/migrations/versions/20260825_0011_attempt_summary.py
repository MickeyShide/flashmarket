"""Expose current attempt state on the compatibility aggregate.

Revision ID: 20260825_0011
Revises: 20260825_0010
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0011"
down_revision: str | Sequence[str] | None = "20260825_0010"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("current_attempt_status", sa.String(20), nullable=True))
    connection = op.get_bind()
    payments = sa.table(
        "payments",
        sa.column("id", sa.Uuid()),
        sa.column("current_attempt_id", sa.Uuid()),
        sa.column("current_attempt_status", sa.String()),
    )
    attempts = sa.table(
        "payment_attempts",
        sa.column("id", sa.Uuid()),
        sa.column("status", sa.String()),
    )
    status_query = (
        sa.select(attempts.c.status)
        .where(attempts.c.id == payments.c.current_attempt_id)
        .scalar_subquery()
    )
    connection.execute(
        payments.update()
        .where(payments.c.current_attempt_id.is_not(None))
        .values(current_attempt_status=status_query)
    )


def downgrade() -> None:
    op.drop_column("payments", "current_attempt_status")
