"""add_brands

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "brands",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("logo_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_brands_slug", "brands", ["slug"])

    op.add_column("products", sa.Column("brand_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_products_brand_id_brands",
        "products",
        "brands",
        ["brand_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_products_brand_id", "products", ["brand_id"])
    op.create_index("ix_products_brand_status", "products", ["brand_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_products_brand_status", table_name="products")
    op.drop_index("ix_products_brand_id", table_name="products")
    op.drop_constraint("fk_products_brand_id_brands", "products", type_="foreignkey")
    op.drop_column("products", "brand_id")
    op.drop_index("ix_brands_slug", table_name="brands")
    op.drop_table("brands")
