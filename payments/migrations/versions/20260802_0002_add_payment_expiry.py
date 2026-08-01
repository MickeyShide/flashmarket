"""Add authoritative payment deadline.

Revision ID: 20260802_0002
Revises: 20260729_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260802_0002"
down_revision: str | Sequence[str] | None = "20260729_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("payments", sa.Column("expires_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("payments", "expires_at")
