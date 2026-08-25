"""Add normalized payment attempts.

Revision ID: 20260825_0009
Revises: 20260825_0008
Create Date: 2026-08-25
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0009"
down_revision: str | Sequence[str] | None = "20260825_0008"
branch_labels = depends_on = None

ACTIVE_ATTEMPT_SQL = "status IN ('NEW','PREPARING','UNKNOWN','PENDING')"


def upgrade() -> None:
    op.add_column("payments", sa.Column("current_attempt_id", sa.Uuid(), nullable=True))
    op.create_index("ix_payments_current_attempt_id", "payments", ["current_attempt_id"])
    op.create_table(
        "payment_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), server_default="NEW", nullable=False),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("external_status", sa.String(64), nullable=True),
        sa.Column("confirmation_url", sa.String(2048), nullable=True),
        sa.Column("cancellation_party", sa.String(64), nullable=True),
        sa.Column("cancellation_reason", sa.String(255), nullable=True),
        sa.Column("provider_test", sa.Boolean(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount > 0", name="ck_payment_attempts_amount_positive"),
        sa.CheckConstraint("attempt_number > 0", name="ck_payment_attempts_number_positive"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_id", "attempt_number", name="uq_payment_attempts_number"),
    )
    op.create_index("ix_payment_attempts_payment_id", "payment_attempts", ["payment_id"])
    op.create_index("ix_payment_attempts_external_id", "payment_attempts", ["external_id"])
    op.create_index("ix_payment_attempts_expires_at", "payment_attempts", ["expires_at"])
    op.create_index(
        "uq_payment_attempts_active",
        "payment_attempts",
        ["payment_id"],
        unique=True,
        postgresql_where=sa.text(ACTIVE_ATTEMPT_SQL),
        sqlite_where=sa.text(ACTIVE_ATTEMPT_SQL),
    )

    connection = op.get_bind()
    payments = sa.table(
        "payments",
        sa.column("id", sa.Uuid()),
        sa.column("amount", sa.Integer()),
        sa.column("currency", sa.String()),
        sa.column("provider", sa.String()),
        sa.column("status", sa.String()),
        sa.column("external_id", sa.String()),
        sa.column("external_status", sa.String()),
        sa.column("confirmation_url", sa.String()),
        sa.column("cancellation_reason", sa.String()),
        sa.column("provider_test", sa.Boolean()),
        sa.column("expires_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
        sa.column("current_attempt_id", sa.Uuid()),
    )
    attempts = sa.table(
        "payment_attempts",
        sa.column("id", sa.Uuid()),
        sa.column("payment_id", sa.Uuid()),
        sa.column("attempt_number", sa.Integer()),
        sa.column("amount", sa.Integer()),
        sa.column("currency", sa.String()),
        sa.column("provider", sa.String()),
        sa.column("status", sa.String()),
        sa.column("external_id", sa.String()),
        sa.column("external_status", sa.String()),
        sa.column("confirmation_url", sa.String()),
        sa.column("cancellation_reason", sa.String()),
        sa.column("provider_test", sa.Boolean()),
        sa.column("expires_at", sa.DateTime(timezone=True)),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    provider_operations = sa.table(
        "provider_operations",
        sa.column("operation_type", sa.String()),
        sa.column("payment_id", sa.Uuid()),
        sa.column("entity_id", sa.Uuid()),
    )
    status_map = {
        "PENDING": "NEW",
        "SUCCESS": "SUCCEEDED",
        "FAILED": "FAILED",
        "CANCELLED": "CANCELED",
        "REFUNDED": "SUCCEEDED",
    }
    for payment in connection.execute(sa.select(payments)).mappings():
        attempt_id = uuid.uuid4()
        attempt_status = status_map.get(str(payment["status"]), "FAILED")
        if payment["status"] == "PENDING" and payment["confirmation_url"]:
            attempt_status = "PENDING"
        connection.execute(
            attempts.insert().values(
                id=attempt_id,
                payment_id=payment["id"],
                attempt_number=1,
                amount=payment["amount"],
                currency=payment["currency"],
                provider=payment["provider"],
                status=attempt_status,
                external_id=payment["external_id"],
                external_status=payment["external_status"],
                confirmation_url=payment["confirmation_url"],
                cancellation_reason=payment["cancellation_reason"],
                provider_test=payment["provider_test"],
                expires_at=payment["expires_at"],
                created_at=payment["created_at"],
                updated_at=payment["updated_at"],
            )
        )
        connection.execute(
            payments.update()
            .where(payments.c.id == payment["id"])
            .values(current_attempt_id=attempt_id)
        )
        connection.execute(
            provider_operations.update()
            .where(
                provider_operations.c.payment_id == payment["id"],
                provider_operations.c.operation_type == "create_payment",
            )
            .values(entity_id=attempt_id)
        )


def downgrade() -> None:
    op.drop_index("uq_payment_attempts_active", table_name="payment_attempts")
    op.drop_index("ix_payment_attempts_expires_at", table_name="payment_attempts")
    op.drop_index("ix_payment_attempts_external_id", table_name="payment_attempts")
    op.drop_index("ix_payment_attempts_payment_id", table_name="payment_attempts")
    op.drop_table("payment_attempts")
    op.drop_index("ix_payments_current_attempt_id", table_name="payments")
    op.drop_column("payments", "current_attempt_id")
