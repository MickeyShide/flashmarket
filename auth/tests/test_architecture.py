import ast
from pathlib import Path


def test_application_layer_does_not_import_framework_or_persistence_adapters() -> None:
    application_root = Path(__file__).parents[1] / "src" / "auth_service" / "application"
    forbidden_prefixes = (
        "fastapi",
        "redis",
        "sqlalchemy",
        "auth_service.api",
        "auth_service.cache",
        "auth_service.database",
        "auth_service.infrastructure",
    )
    violations: list[str] = []

    for path in application_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported_modules: list[str] = []
            if isinstance(node, ast.Import):
                imported_modules.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)
            for module in imported_modules:
                if module.startswith(forbidden_prefixes):
                    violations.append(f"{path.relative_to(application_root)} imports {module}")

    assert violations == []
