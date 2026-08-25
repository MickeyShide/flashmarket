"""Add unique constraint on payments order_id.

Revision ID: 20260819_0005
Revises: 20260813_0004
Create Date: 2026-08-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260819_0005"
down_revision: str | Sequence[str] | None = "20260813_0004"
branch_labels = depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("payments") as batch_op:
        batch_op.create_unique_constraint(
            "uq_payments_order_id",
            ["order_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_constraint(
            "uq_payments_order_id",
            type_="unique",
        )
