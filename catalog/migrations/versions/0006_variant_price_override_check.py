"""Add check constraint for product variant price_override.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_product_variants_price_override_positive",
        "product_variants",
        "price_override IS NULL OR price_override > 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_product_variants_price_override_positive",
        "product_variants",
        type_="check",
    )
