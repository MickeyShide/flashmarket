"""Add promocodes and promocode_usages tables, update orders table

Revision ID: 20260731_0002
Revises: 20260729_0001
Create Date: 2026-07-31 12:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0002"
down_revision: str | Sequence[str] | None = "20260729_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create promocodes table
    op.create_table(
        "promocodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("discount_type", sa.String(length=20), nullable=False),
        sa.Column("discount_value", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="RUB"),
        sa.Column("min_order_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("max_discount_amount", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("max_uses_per_user", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("discount_value > 0", name="ck_promocodes_value_positive"),
        sa.CheckConstraint("current_uses >= 0", name="ck_promocodes_uses_non_negative"),
        sa.CheckConstraint("expires_at > starts_at", name="ck_promocodes_valid_period"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_promocodes_code", "promocodes", ["code"])

    # 2. Create promocode_usages table
    op.create_table(
        "promocode_usages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("promocode_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["promocode_id"], ["promocodes.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
        sa.UniqueConstraint("promocode_id", "order_id", name="uq_usage_promocode_order"),
    )
    op.create_index("ix_promocode_usages_promocode_id", "promocode_usages", ["promocode_id"])
    op.create_index("ix_promocode_usages_user_id", "promocode_usages", ["user_id"])
    op.create_index(
        "ix_usage_promocode_user", "promocode_usages", ["promocode_id", "user_id"]
    )

    # 3. Add promocode columns to orders table
    op.add_column("orders", sa.Column("original_price", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column(
        "orders",
        sa.Column(
            "discount_amount",
            sa.Numeric(precision=12, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column("orders", sa.Column("final_price", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column("orders", sa.Column("promocode_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_orders_promocode_id", "orders", "promocodes", ["promocode_id"], ["id"])
    op.create_index("ix_orders_promocode_id", "orders", ["promocode_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_promocode_id", table_name="orders")
    op.drop_constraint("fk_orders_promocode_id", "orders", type_="foreignkey")
    op.drop_column("orders", "promocode_id")
    op.drop_column("orders", "final_price")
    op.drop_column("orders", "discount_amount")
    op.drop_column("orders", "original_price")

    op.drop_index("ix_usage_promocode_user", table_name="promocode_usages")
    op.drop_index("ix_promocode_usages_user_id", table_name="promocode_usages")
    op.drop_index("ix_promocode_usages_promocode_id", table_name="promocode_usages")
    op.drop_table("promocode_usages")

    op.drop_index("ix_promocodes_code", table_name="promocodes")
    op.drop_table("promocodes")
