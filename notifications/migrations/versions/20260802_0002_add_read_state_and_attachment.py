"""Add notification read state, attachment and event idempotency key.

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
    op.add_column("notifications", sa.Column("attachment_url", sa.String(2048)))
    op.add_column("notifications", sa.Column("event_key", sa.String(255)))
    op.add_column("notifications", sa.Column("read_at", sa.DateTime(timezone=True)))
    op.create_index("ix_notifications_event_key", "notifications", ["event_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_notifications_event_key", table_name="notifications")
    op.drop_column("notifications", "read_at")
    op.drop_column("notifications", "event_key")
    op.drop_column("notifications", "attachment_url")
