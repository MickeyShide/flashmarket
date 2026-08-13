"""Add bounded outbox retry scheduling."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_outbox_retry"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels = depends_on = None


def upgrade() -> None:
    op.add_column("outbox_events", sa.Column("next_attempt_at", sa.DateTime(timezone=True)))
    op.add_column("outbox_events", sa.Column("last_error", sa.Text()))
    op.add_column("outbox_events", sa.Column("claim_token", sa.Uuid()))
    op.add_column("outbox_events", sa.Column("claimed_until", sa.DateTime(timezone=True)))
    op.create_index(
        "ix_drops_outbox_due", "outbox_events", ["status", "next_attempt_at", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_drops_outbox_due", table_name="outbox_events")
    op.drop_column("outbox_events", "last_error")
    op.drop_column("outbox_events", "claimed_until")
    op.drop_column("outbox_events", "claim_token")
    op.drop_column("outbox_events", "next_attempt_at")
