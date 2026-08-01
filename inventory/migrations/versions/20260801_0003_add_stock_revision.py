"""Add a monotonic revision to stock rows.

Revision ID: 20260801_0003
Revises: 20260731_0002
Create Date: 2026-08-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0003"
down_revision: str | Sequence[str] | None = "20260731_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the revision column and initialize existing rows."""
    op.add_column(
        "stocks",
        sa.Column("revision", sa.Integer(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    """Remove the revision column."""
    op.drop_column("stocks", "revision")
