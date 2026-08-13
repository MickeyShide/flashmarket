"""Initial migration for drops service

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-31 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. drops table
    op.create_table(
        "drops",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("cover_image", sa.String(length=2048), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_per_user", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payment_timeout_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("ends_at > starts_at", name="ck_drops_valid_time_range"),
        sa.CheckConstraint("max_per_user >= 1", name="ck_drops_max_per_user_positive"),
        sa.CheckConstraint("payment_timeout_seconds >= 60", name="ck_drops_payment_timeout_min"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_drops_slug", "drops", ["slug"])
    op.create_index("ix_drops_status", "drops", ["status"])
    op.create_index("ix_drops_starts_at", "drops", ["starts_at"])

    # 2. drop_items table
    op.create_table(
        "drop_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("drop_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["drop_id"], ["drops.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("drop_id", "product_id", name="uq_drop_items_drop_product"),
    )
    op.create_index("ix_drop_items_drop_id", "drop_items", ["drop_id"])

    # 3. outbox_events table
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_outbox_events_status_created_at", "outbox_events", ["status", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_outbox_events_status_created_at", table_name="outbox_events")
    op.drop_table("outbox_events")

    op.drop_index("ix_drop_items_drop_id", table_name="drop_items")
    op.drop_table("drop_items")

    op.drop_index("ix_drops_starts_at", table_name="drops")
    op.drop_index("ix_drops_status", table_name="drops")
    op.drop_index("ix_drops_slug", table_name="drops")
    op.drop_table("drops")
