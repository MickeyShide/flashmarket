"""Add consumer inbox deduplication."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_consumer_inbox"
down_revision: str | Sequence[str] | None = "0002_transactional_outbox"
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
