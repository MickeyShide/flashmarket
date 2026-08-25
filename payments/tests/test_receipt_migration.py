"""Migration coverage for durable receipt delivery states."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import uuid
from pathlib import Path


def _alembic(payments_root: Path, database_path: Path, *args: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "PAYMENTS_DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
            "PAYMENTS_ENVIRONMENT": "test",
            "PAYMENTS_PAYMENT_PROVIDER": "mock",
        }
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(payments_root / "alembic.ini"), *args],
        cwd=payments_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )


def test_receipt_status_migration_upgrade_and_downgrade(tmp_path: Path) -> None:
    payments_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path / "receipt-migration.db"
    _alembic(payments_root, database_path, "upgrade", "20260825_0014")

    now = "2026-08-25 00:00:00"
    rows = [
        (uuid.uuid4().hex, uuid.uuid4().hex, "SIMULATED"),
        (uuid.uuid4().hex, uuid.uuid4().hex, "NEEDS_CONTACT"),
    ]
    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            """
            INSERT INTO payment_receipts
                (id, payment_id, snapshot, snapshot_hash, status, created_at, updated_at)
            VALUES (?, ?, '{}', ?, ?, ?, ?)
            """,
            [
                (receipt_id, payment_id, "0" * 64, status, now, now)
                for receipt_id, payment_id, status in rows
            ],
        )

    _alembic(payments_root, database_path, "upgrade", "head")
    with sqlite3.connect(database_path) as connection:
        statuses = connection.execute(
            "SELECT status FROM payment_receipts ORDER BY status"
        ).fetchall()
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        assert statuses == [("NEEDS_CONTACT",), ("READY",)]
        assert revision == ("20260825_0015",)
        connection.execute(
            "UPDATE payment_receipts SET status = 'SUBMITTED' WHERE status = 'READY'"
        )

    _alembic(payments_root, database_path, "downgrade", "20260825_0014")
    with sqlite3.connect(database_path) as connection:
        statuses = connection.execute(
            "SELECT status FROM payment_receipts ORDER BY status"
        ).fetchall()
        assert statuses == [("NEEDS_CONTACT",), ("SIMULATED",)]
