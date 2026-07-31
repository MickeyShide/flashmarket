"""Add product_variants table

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-31

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=100), nullable=False),
        sa.Column("size", sa.String(length=20), nullable=True),
        sa.Column("color", sa.String(length=50), nullable=True),
        sa.Column("color_hex", sa.String(length=7), nullable=True),
        sa.Column("material", sa.String(length=100), nullable=True),
        sa.Column("weight_grams", sa.Integer(), nullable=True),
        sa.Column("price_override", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
        sa.UniqueConstraint("product_id", "size", "color", name="uq_variant_product_size_color"),
    )
    op.create_index("ix_product_variants_sku", "product_variants", ["sku"])
    op.create_index(
        "ix_variants_product_active", "product_variants", ["product_id", "is_active"]
    )


def downgrade() -> None:
    op.drop_index("ix_variants_product_active", table_name="product_variants")
    op.drop_index("ix_product_variants_sku", table_name="product_variants")
    op.drop_table("product_variants")
