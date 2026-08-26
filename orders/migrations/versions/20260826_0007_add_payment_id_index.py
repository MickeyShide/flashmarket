"""Add index on orders payment_id.

Revision ID: 20260826_0007
Revises: 20260817_0006
Create Date: 2026-08-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260826_0007"
down_revision: str | Sequence[str] | None = "20260817_0006"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_orders_payment_id",
        "orders",
        ["payment_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_orders_payment_id",
        "orders",
    )
