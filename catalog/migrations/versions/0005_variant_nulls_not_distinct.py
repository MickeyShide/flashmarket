"""Enforce NULLS NOT DISTINCT on uq_variant_product_size_color.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-19
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    try:
        op.drop_constraint("uq_variant_product_size_color", "product_variants", type_="unique")
    except Exception:
        pass
    op.create_unique_constraint(
        "uq_variant_product_size_color",
        "product_variants",
        ["product_id", "size", "color"],
        postgresql_nulls_not_distinct=True,
    )


def downgrade() -> None:
    try:
        op.drop_constraint("uq_variant_product_size_color", "product_variants", type_="unique")
    except Exception:
        pass
    op.create_unique_constraint(
        "uq_variant_product_size_color",
        "product_variants",
        ["product_id", "size", "color"],
    )
