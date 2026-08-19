"""Enforce NULLS NOT DISTINCT on uq_stocks_product_variant.

Revision ID: 20260819_0007
Revises: 20260813_0006
Create Date: 2026-08-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260819_0007"
down_revision: str | Sequence[str] | None = "20260813_0006"
branch_labels = depends_on = None


def upgrade() -> None:
    # Drop existing constraint
    try:
        op.drop_constraint("uq_stocks_product_variant", "stocks", type_="unique")
    except Exception:
        pass

    # Recreate with postgresql_nulls_not_distinct=True
    op.create_unique_constraint(
        "uq_stocks_product_variant",
        "stocks",
        ["product_id", "variant_id"],
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    try:
        op.drop_constraint("uq_stocks_product_variant", "stocks", type_="unique")
    except Exception:
        pass
    op.create_unique_constraint(
        "uq_stocks_product_variant",
        "stocks",
        ["product_id", "variant_id"],
    )
