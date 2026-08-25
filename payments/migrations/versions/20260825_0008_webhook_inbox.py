"""Add durable webhook inbox.

Revision ID: 20260825_0008
Revises: 20260825_0007
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0008"
down_revision: str | Sequence[str] | None = "20260825_0007"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_inbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("object_type", sa.String(32), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("event", sa.String(64), nullable=True),
        sa.Column("target_status", sa.String(64), nullable=True),
        sa.Column("dedupe_hash", sa.String(64), nullable=False),
        sa.Column("raw_body", sa.Text(), nullable=False),
        sa.Column("source_ip", sa.String(64), nullable=True),
        sa.Column("status", sa.String(20), server_default="PENDING", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_token", sa.Uuid(), nullable=True),
        sa.Column("claimed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(128), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("attempt_count >= 0", name="ck_webhook_inbox_attempts"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_hash", name="uq_webhook_inbox_dedupe_hash"),
    )
    op.create_index("ix_webhook_inbox_external_id", "webhook_inbox", ["external_id"])
    op.create_index(
        "ix_webhook_inbox_due",
        "webhook_inbox",
        ["status", "next_attempt_at", "received_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_inbox_due", table_name="webhook_inbox")
    op.drop_index("ix_webhook_inbox_external_id", table_name="webhook_inbox")
    op.drop_table("webhook_inbox")
