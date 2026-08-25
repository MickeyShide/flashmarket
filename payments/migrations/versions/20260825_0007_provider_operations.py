"""Add durable provider operations.

Revision ID: 20260825_0007
Revises: 20260825_0006
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0007"
down_revision: str | Sequence[str] | None = "20260825_0006"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "provider_operations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("operation_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("request_payload", sa.Text(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), server_default="NEW", nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("first_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claim_token", sa.Uuid(), nullable=True),
        sa.Column("claimed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(64), nullable=True),
        sa.Column("response_payload", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("attempt_count >= 0", name="ck_provider_operations_attempts"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_provider_operations_idempotency_key"),
        sa.UniqueConstraint(
            "operation_type", "entity_id", name="uq_provider_operations_type_entity"
        ),
    )
    op.create_index(
        "ix_provider_operations_entity_id",
        "provider_operations",
        ["entity_id"],
    )
    op.create_index(
        "ix_provider_operations_payment_id",
        "provider_operations",
        ["payment_id"],
    )
    op.create_index(
        "ix_provider_operations_external_id",
        "provider_operations",
        ["external_id"],
    )
    op.create_index(
        "ix_provider_operations_recovery",
        "provider_operations",
        ["status", "next_attempt_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_provider_operations_recovery", table_name="provider_operations")
    op.drop_index("ix_provider_operations_external_id", table_name="provider_operations")
    op.drop_index("ix_provider_operations_payment_id", table_name="provider_operations")
    op.drop_index("ix_provider_operations_entity_id", table_name="provider_operations")
    op.drop_table("provider_operations")
