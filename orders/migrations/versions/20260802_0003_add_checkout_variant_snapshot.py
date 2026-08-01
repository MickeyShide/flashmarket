"""Add checkout and variant snapshot fields to orders.

Revision ID: 20260802_0003
Revises: 20260731_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0003"
down_revision: str | Sequence[str] | None = "20260731_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("checkout_id", sa.Uuid(), nullable=True))
    op.add_column("orders", sa.Column("variant_id", sa.Uuid(), nullable=True))
    op.add_column("orders", sa.Column("variant_sku", sa.String(length=100), nullable=True))
    op.add_column("orders", sa.Column("variant_size", sa.String(length=20), nullable=True))
    op.add_column("orders", sa.Column("variant_color", sa.String(length=50), nullable=True))
    op.add_column("orders", sa.Column("drop_id", sa.Uuid(), nullable=True))
    op.add_column(
        "orders", sa.Column("payment_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index("ix_orders_checkout_id", "orders", ["checkout_id"])
    op.create_index("ix_orders_drop_id", "orders", ["drop_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_drop_id", table_name="orders")
    op.drop_index("ix_orders_checkout_id", table_name="orders")
    for column in (
        "payment_expires_at",
        "drop_id",
        "variant_color",
        "variant_size",
        "variant_sku",
        "variant_id",
        "checkout_id",
    ):
        op.drop_column("orders", column)
