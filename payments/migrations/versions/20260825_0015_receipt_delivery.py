"""Rename simulated receipt state for real provider delivery.

Revision ID: 20260825_0015
Revises: 20260825_0014
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260825_0015"
down_revision: str | Sequence[str] | None = "20260825_0014"
branch_labels = depends_on = None


def upgrade() -> None:
    receipts = sa.table(
        "payment_receipts",
        sa.column("status", sa.String()),
    )
    op.get_bind().execute(
        receipts.update().where(receipts.c.status == "SIMULATED").values(status="READY")
    )


def downgrade() -> None:
    receipts = sa.table(
        "payment_receipts",
        sa.column("status", sa.String()),
    )
    op.get_bind().execute(
        receipts.update()
        .where(receipts.c.status.in_(("READY", "SUBMITTED")))
        .values(status="SIMULATED")
    )
