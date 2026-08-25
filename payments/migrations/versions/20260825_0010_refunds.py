"""Add normalized refunds.

Revision ID: 20260825_0010
Revises: 20260825_0009
Create Date: 2026-08-25
"""

import hashlib
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0010"
down_revision: str | Sequence[str] | None = "20260825_0009"
branch_labels = depends_on = None


def upgrade() -> None:
    op.create_table(
        "refunds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("parent_refund_id", sa.Uuid(), nullable=True),
        sa.Column("request_key", sa.String(64), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), server_default="NEW", nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("external_status", sa.String(64), nullable=True),
        sa.Column("cancellation_party", sa.String(64), nullable=True),
        sa.Column("cancellation_reason", sa.String(255), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("claim_token", sa.Uuid(), nullable=True),
        sa.Column("claimed_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_refunds_amount_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_key", name="uq_refunds_request_key"),
    )
    op.create_index("ix_refunds_payment_id", "refunds", ["payment_id"])
    op.create_index("ix_refunds_parent_refund_id", "refunds", ["parent_refund_id"])
    op.create_index("ix_refunds_external_id", "refunds", ["external_id"], unique=True)
    op.create_index("ix_refunds_reconcile", "refunds", ["status", "next_attempt_at", "created_at"])

    connection = op.get_bind()
    payments = sa.table(
        "payments",
        sa.column("id", sa.Uuid()),
        sa.column("amount", sa.Integer()),
        sa.column("currency", sa.String()),
        sa.column("refund_external_id", sa.String()),
        sa.column("refund_status", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    refunds = sa.table(
        "refunds",
        sa.column("id", sa.Uuid()),
        sa.column("payment_id", sa.Uuid()),
        sa.column("request_key", sa.String()),
        sa.column("amount", sa.Integer()),
        sa.column("currency", sa.String()),
        sa.column("reason", sa.String()),
        sa.column("status", sa.String()),
        sa.column("external_id", sa.String()),
        sa.column("external_status", sa.String()),
        sa.column("attempt_count", sa.Integer()),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    for payment in connection.execute(
        sa.select(payments).where(payments.c.refund_external_id.is_not(None))
    ).mappings():
        request_key = hashlib.sha256(
            f"legacy:{payment['id']}:{payment['refund_external_id']}".encode()
        ).hexdigest()
        external_status = str(payment["refund_status"] or "pending")
        connection.execute(
            refunds.insert().values(
                id=uuid.uuid4(),
                payment_id=payment["id"],
                request_key=request_key,
                amount=payment["amount"],
                currency=payment["currency"],
                reason="legacy_refund",
                status="SUCCEEDED" if external_status == "succeeded" else "PENDING",
                external_id=payment["refund_external_id"],
                external_status=external_status,
                attempt_count=1,
                created_at=payment["created_at"],
                updated_at=payment["updated_at"],
            )
        )


def downgrade() -> None:
    op.drop_index("ix_refunds_reconcile", table_name="refunds")
    op.drop_index("ix_refunds_external_id", table_name="refunds")
    op.drop_index("ix_refunds_parent_refund_id", table_name="refunds")
    op.drop_index("ix_refunds_payment_id", table_name="refunds")
    op.drop_table("refunds")
