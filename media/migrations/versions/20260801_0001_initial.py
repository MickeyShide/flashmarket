"""Create media assets.

Revision ID: 20260801_0001
Revises:
Create Date: 2026-08-01 19:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260801_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "media_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("uploader_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("visibility", sa.String(length=16), nullable=False),
        sa.Column("bucket", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("declared_content_type", sa.String(length=255), nullable=False),
        sa.Column("detected_content_type", sa.String(length=255), nullable=True),
        sa.Column("expected_size", sa.BigInteger(), nullable=False),
        sa.Column("actual_size", sa.BigInteger(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("upload_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delete_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("actual_size IS NULL OR actual_size > 0", name="ck_media_actual_size_positive"),
        sa.CheckConstraint("expected_size > 0", name="ck_media_expected_size_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key"),
    )
    op.create_index("ix_media_assets_uploader_id", "media_assets", ["uploader_id"])
    op.create_index("ix_media_uploader_created", "media_assets", ["uploader_id", "created_at"])
    op.create_index(
        "ix_media_entity", "media_assets", ["entity_type", "entity_id", "purpose", "status"]
    )
    op.create_index("ix_media_expiration", "media_assets", ["status", "upload_expires_at"])
    op.create_index("ix_media_deletion", "media_assets", ["status", "delete_requested_at"])


def downgrade() -> None:
    op.drop_index("ix_media_deletion", table_name="media_assets")
    op.drop_index("ix_media_expiration", table_name="media_assets")
    op.drop_index("ix_media_entity", table_name="media_assets")
    op.drop_index("ix_media_uploader_created", table_name="media_assets")
    op.drop_index("ix_media_assets_uploader_id", table_name="media_assets")
    op.drop_table("media_assets")
