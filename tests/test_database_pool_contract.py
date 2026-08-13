"""Contracts for bounded SQLAlchemy pools in every service."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATABASE_MODULES = (
    "auth/src/auth_service/database.py",
    "catalog/src/catalog/infrastructure/database.py",
    "inventory/src/inventory/infrastructure/database.py",
    "orders/src/orders/infrastructure/database.py",
    "payments/src/payments/infrastructure/database.py",
    "notifications/src/notifications/infrastructure/database.py",
    "wishlist/src/wishlist/infrastructure/database.py",
    "drops/src/drops/infrastructure/database.py",
    "media/src/media_service/infrastructure/database.py",
)


def test_every_database_engine_has_role_based_bounded_pool() -> None:
    for relative_path in DATABASE_MODULES:
        content = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
        assert "FLASHMARKET_PROCESS_ROLE" in content, relative_path
        assert '"pool_size"' in content, relative_path
        assert '"max_overflow"' in content, relative_path
        assert '"pool_timeout"' in content, relative_path
        assert '"pool_recycle"' in content, relative_path


def test_entrypoint_assigns_api_and_worker_roles_before_exec() -> None:
    content = (PROJECT_ROOT / "docker/entrypoint.sh").read_text(encoding="utf-8")
    assert "export FLASHMARKET_PROCESS_ROLE=api" in content
    assert content.count("export FLASHMARKET_PROCESS_ROLE=worker") >= 4
