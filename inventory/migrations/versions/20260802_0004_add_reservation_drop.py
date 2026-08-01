"""Add Drop identity to reservations.

Revision ID: 20260802_0004
Revises: 20260801_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0004"
down_revision: str | Sequence[str] | None = "20260801_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reservations", sa.Column("drop_id", sa.Uuid(), nullable=True))
    op.create_index("ix_reservations_drop_id", "reservations", ["drop_id"])


def downgrade() -> None:
    op.drop_index("ix_reservations_drop_id", table_name="reservations")
    op.drop_column("reservations", "drop_id")
