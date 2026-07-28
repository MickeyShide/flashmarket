"""Require trimmed lowercase email addresses.

Revision ID: 20260728_0004
Revises: 20260728_0003
Create Date: 2026-07-28 18:00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260728_0004"
down_revision: str | None = "20260728_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Normalize existing emails and enforce the canonical representation."""
    op.drop_constraint("ck_users_email_normalized", "users", type_="check")
    op.execute("UPDATE users SET email = lower(trim(email))")
    op.create_check_constraint(
        "ck_users_email_normalized",
        "users",
        "email = lower(trim(email))",
    )


def downgrade() -> None:
    """Restore the previous lowercase-only email constraint."""
    op.drop_constraint("ck_users_email_normalized", "users", type_="check")
    op.create_check_constraint(
        "ck_users_email_normalized",
        "users",
        "email = lower(email)",
    )
