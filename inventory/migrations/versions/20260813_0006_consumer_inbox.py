"""Add consumer inbox deduplication.

Revision ID: 20260813_0006
Revises: 20260813_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0006"
down_revision: str | Sequence[str] | None = "20260813_0005"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_events",
        sa.Column("event_id", sa.String(128), primary_key=True),
        sa.Column("routing_key", sa.String(255), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("processed_events")
