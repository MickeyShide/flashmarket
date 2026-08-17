"""Add unique constraint on orders reservation_id.

Revision ID: 20260817_0006
Revises: 20260813_0005
Create Date: 2026-08-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260817_0006"
down_revision: str | Sequence[str] | None = "20260813_0005"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_orders_reservation_id",
        "orders",
        ["reservation_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_orders_reservation_id",
        "orders",
        type_="unique",
    )
