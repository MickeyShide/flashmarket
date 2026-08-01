"""Export one FastAPI application schema without starting its lifespan."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from fastapi.routing import iter_route_contexts

ACCESS_LEVELS = {"anonymous", "authenticated", "admin"}


def _dependency_names(route: Any) -> set[str]:
    """Return callable names from the complete FastAPI dependency tree."""
    names: set[str] = set()
    pending = list(route.dependant.dependencies)
    while pending:
        dependency = pending.pop()
        call = dependency.call
        if call is not None:
            name = getattr(call, "__name__", "")
            qualname = getattr(call, "__qualname__", "")
            if name:
                names.add(name)
            if qualname:
                names.add(qualname)
        pending.extend(dependency.dependencies)
    return names


def _infer_access(route: Any) -> str:
    """Infer public access from the project's standard auth dependencies."""
    explicit = (route.openapi_extra or {}).get("x-flashmarket-access")
    if explicit is not None:
        if explicit not in ACCESS_LEVELS:
            raise ValueError(
                f"Invalid x-flashmarket-access={explicit!r} on {route.path}"
            )
        return str(explicit)

    dependencies = _dependency_names(route)
    short_names = {name.rsplit(".", 1)[-1] for name in dependencies}
    if "require_admin" in short_names:
        return "admin"
    if "get_current_principal" in short_names:
        return "authenticated"
    return "anonymous"


def _access_map(app: Any) -> dict[tuple[str, str], str]:
    access_by_operation: dict[tuple[str, str], str] = {}
    for route in iter_route_contexts(app.routes):
        if not getattr(route, "include_in_schema", False):
            continue
        access = _infer_access(route)
        if "/admin" in route.path and access != "admin":
            raise ValueError(
                f"Admin path {route.path!r} is missing the admin dependency"
            )
        for method in route.methods or ():
            access_by_operation[(route.path, method.lower())] = access
    return access_by_operation


def _prepare_auth_keys() -> tempfile.TemporaryDirectory[str]:
    """Create an ephemeral Ed25519 pair required by the Auth app factory."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    temporary_directory = tempfile.TemporaryDirectory(prefix="flashmarket-openapi-auth-")
    keys_directory = Path(temporary_directory.name)
    private_directory = keys_directory / "private"
    public_directory = keys_directory / "public"
    private_directory.mkdir(parents=True)
    public_directory.mkdir(parents=True)

    key_id = "flashmarket-auth-ed25519-v1"
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    (private_directory / f"{key_id}.pem").write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    (public_directory / f"{key_id}.pem").write_bytes(
        public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )
    os.environ["AUTH_JWT_KEYS_DIRECTORY"] = str(keys_directory)
    os.environ["AUTH_JWT_KEY_ID"] = key_id
    return temporary_directory


def export_schema(module_name: str, service: str) -> dict[str, Any]:
    """Import an application and return its annotated OpenAPI document."""
    prefix = service.upper().replace("-", "_")
    os.environ[f"{prefix}_ENVIRONMENT"] = "development"
    os.environ[f"{prefix}_DOCS_ENABLED"] = "true"

    auth_keys = _prepare_auth_keys() if service == "auth" else None
    try:
        module = importlib.import_module(module_name)
        app = getattr(module, "app", None)
        if app is None:
            factory = getattr(module, "create_app", None)
            if factory is None:
                raise ValueError(f"{module_name} exposes neither app nor create_app")
            app = factory()
        app.openapi_schema = None
        access_by_operation = _access_map(app)
        schema = app.openapi()
        if not isinstance(schema, dict):
            raise TypeError(f"{module_name}.app.openapi() returned a non-object")
        for (path, method), access in access_by_operation.items():
            operation = schema.get("paths", {}).get(path, {}).get(method)
            if isinstance(operation, dict):
                operation["x-flashmarket-access"] = access
        return schema
    finally:
        if auth_keys is not None:
            auth_keys.cleanup()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    document = export_schema(args.module, args.service)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
