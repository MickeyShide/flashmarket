"""Add variant_id column to stocks table and update unique constraint

Revision ID: 20260731_0002
Revises: 20260729_0001
Create Date: 2026-07-31

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0002"
down_revision: str | Sequence[str] | None = "20260729_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Drop old unique constraint & unique index on product_id
    try:
        op.drop_constraint("uq_stocks_product_id", "stocks", type_="unique")
    except Exception:
        pass
    try:
        op.drop_index("ix_stocks_product_id", table_name="stocks")
        op.create_index("ix_stocks_product_id", "stocks", ["product_id"], unique=False)
    except Exception:
        pass

    # 2. Add variant_id column
    op.add_column("stocks", sa.Column("variant_id", sa.Uuid(), nullable=True))
    op.create_index("ix_stocks_variant_id", "stocks", ["variant_id"])

    # 3. Add composite unique constraint for product_id + variant_id
    op.create_unique_constraint(
        "uq_stocks_product_variant", "stocks", ["product_id", "variant_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_stocks_product_variant", "stocks", type_="unique")
    op.drop_index("ix_stocks_variant_id", table_name="stocks")
    op.drop_column("stocks", "variant_id")
    op.drop_index("ix_stocks_product_id", table_name="stocks")
    op.create_index("ix_stocks_product_id", "stocks", ["product_id"], unique=True)
    op.create_unique_constraint("uq_stocks_product_id", "stocks", ["product_id"])
