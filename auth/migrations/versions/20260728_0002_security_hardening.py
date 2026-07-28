"""Add normalized emails and security audit events.

Revision ID: 20260728_0002
Revises: 20260728_0001
Create Date: 2026-07-28 15:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0002"
down_revision: str | None = "20260728_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply this revision’s schema changes."""
    op.execute("UPDATE users SET email = lower(email)")
    op.create_check_constraint(
        "ck_users_email_normalized",
        "users",
        "email = lower(email)",
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("subject_user_id", sa.Uuid(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("event_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_audit_events_actor_user_id_users",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["subject_user_id"],
            ["users.id"],
            name="fk_audit_events_subject_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )
    op.create_index(
        "ix_audit_events_type_created",
        "audit_events",
        ["event_type", "created_at"],
    )
    op.create_index(
        "ix_audit_events_actor_created",
        "audit_events",
        ["actor_user_id", "created_at"],
    )
    op.create_index(
        "ix_audit_events_subject_created",
        "audit_events",
        ["subject_user_id", "created_at"],
    )


def downgrade() -> None:
    """Revert this revision’s schema changes."""
    op.drop_index("ix_audit_events_subject_created", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_created", table_name="audit_events")
    op.drop_index("ix_audit_events_type_created", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_constraint("ck_users_email_normalized", "users", type_="check")
