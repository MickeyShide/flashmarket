"""Initial inventory schema.

Revision ID: 20260729_0001
Revises:
Create Date: 2026-07-29 00:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260729_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply this revision's schema changes."""
    op.create_table(
        "stocks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("available", sa.Integer(), nullable=False),
        sa.Column("reserved", sa.Integer(), nullable=False),
        sa.Column("sold", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_stocks"),
        sa.UniqueConstraint("product_id", name="uq_stocks_product_id"),
    )
    op.create_index("ix_stocks_product_id", "stocks", ["product_id"], unique=True)

    op.create_table(
        "reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("stock_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["stock_id"],
            ["stocks.id"],
            name="fk_reservations_stock_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reservations"),
    )
    op.create_index("ix_reservations_stock_id", "reservations", ["stock_id"])
    op.create_index("ix_reservations_user_id", "reservations", ["user_id"])
    op.create_index("ix_reservations_order_id", "reservations", ["order_id"])
    op.create_index(
        "ix_reservations_status_expires_at",
        "reservations",
        ["status", "expires_at"],
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_outbox_events"),
    )
    op.create_index(
        "ix_outbox_events_status_created_at",
        "outbox_events",
        ["status", "created_at"],
    )

    op.create_check_constraint(
        "ck_stocks_total_non_negative",
        "stocks",
        "total >= 0",
    )
    op.create_check_constraint(
        "ck_stocks_available_non_negative",
        "stocks",
        "available >= 0",
    )
    op.create_check_constraint(
        "ck_stocks_reserved_non_negative",
        "stocks",
        "reserved >= 0",
    )
    op.create_check_constraint(
        "ck_stocks_sold_non_negative",
        "stocks",
        "sold >= 0",
    )
    op.create_check_constraint(
        "ck_stocks_reservation_invariant",
        "stocks",
        "reserved + sold <= total",
    )


def downgrade() -> None:
    """Revert this revision's schema changes."""
    op.drop_index("ix_outbox_events_status_created_at", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_reservations_status_expires_at", table_name="reservations")
    op.drop_index("ix_reservations_order_id", table_name="reservations")
    op.drop_index("ix_reservations_user_id", table_name="reservations")
    op.drop_index("ix_reservations_stock_id", table_name="reservations")
    op.drop_table("reservations")
    op.drop_index("ix_stocks_product_id", table_name="stocks")
    op.drop_table("stocks")
