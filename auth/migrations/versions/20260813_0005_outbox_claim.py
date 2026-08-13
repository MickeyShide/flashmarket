"""Add crash-recoverable outbox claims.

Revision ID: 20260813_0005
Revises: 20260728_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0005"
down_revision: str | Sequence[str] | None = "20260728_0004"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("outbox_events", sa.Column("claim_token", sa.Uuid()))
    op.add_column("outbox_events", sa.Column("claimed_until", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("outbox_events", "claimed_until")
    op.drop_column("outbox_events", "claim_token")
