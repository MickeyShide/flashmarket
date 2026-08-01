"""Generate FlashMarket's same-origin public OpenAPI contract and service index."""

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

HTTP_METHODS = ("get", "post", "put", "patch", "delete", "options", "head", "trace")
ACCESS_LEVELS = {"anonymous", "authenticated", "admin"}
EXCLUDED_PREFIXES = ("/internal", "/metrics", "/health", "/docs", "/redoc", "/openapi.json")
LOCATION_RE = re.compile(r"\blocation\s+(?:(?:=|\^~|~\*?|@\w+)\s+)?([^\s{]+)\s*\{")
UPSTREAM_RE = re.compile(r"set\s+\$upstream_([\w-]+)\s+http://([^:;/\s]+):\d+;")
PACKAGE_RE = re.compile(r"^src/([A-Za-z_][A-Za-z0-9_]*)$")


@dataclass(frozen=True)
class ServiceDefinition:
    id: str
    directory: Path
    module: str
    prefixes: tuple[str, ...]


def _extract_braced_block(content: str, opening_brace: int) -> tuple[str, int]:
    depth = 0
    for index in range(opening_brace, len(content)):
        if content[index] == "{":
            depth += 1
        elif content[index] == "}":
            depth -= 1
            if depth == 0:
                return content[opening_brace + 1 : index], index + 1
    raise ValueError("Unclosed Nginx block")


def main_gateway_server(content: str) -> str:
    marker = "listen 80 default_server;"
    listen_position = content.find(marker)
    if listen_position < 0:
        raise ValueError("gateway/nginx.conf has no default server")
    server_position = content.rfind("server {", 0, listen_position)
    if server_position < 0:
        raise ValueError("Cannot locate the default gateway server")
    opening_brace = content.find("{", server_position)
    block, _ = _extract_braced_block(content, opening_brace)
    return block


def discover_gateway_routes(content: str) -> dict[str, tuple[str, ...]]:
    """Map Docker service names to main-domain public location prefixes."""
    server = main_gateway_server(content)
    routes: dict[str, set[str]] = {}
    for match in LOCATION_RE.finditer(server):
        path = match.group(1)
        opening_brace = server.find("{", match.start())
        block, _ = _extract_braced_block(server, opening_brace)
        upstream = UPSTREAM_RE.search(block)
        if upstream is None:
            continue
        variable_name, docker_name = upstream.groups()
        service = variable_name if variable_name == docker_name else docker_name
        if not path.startswith("/") or path.startswith(EXCLUDED_PREFIXES):
            continue
        routes.setdefault(service, set()).add(path)
    return {
        service: tuple(sorted(prefixes, key=lambda value: (len(value), value)))
        for service, prefixes in sorted(routes.items())
    }


def discover_services(root: Path, gateway_routes: dict[str, tuple[str, ...]]) -> list[ServiceDefinition]:
    services: list[ServiceDefinition] = []
    for service, prefixes in gateway_routes.items():
        directory = root / service
        pyproject_path = directory / "pyproject.toml"
        if not pyproject_path.is_file():
            continue
        with pyproject_path.open("rb") as file:
            pyproject = tomllib.load(file)
        project_name = str(pyproject.get("project", {}).get("name", ""))
        if not project_name.startswith("flashmarket-"):
            continue
        packages = (
            pyproject.get("tool", {})
            .get("hatch", {})
            .get("build", {})
            .get("targets", {})
            .get("wheel", {})
            .get("packages", [])
        )
        package_name = None
        for package in packages:
            package_match = PACKAGE_RE.match(str(package).replace("\\", "/"))
            if package_match:
                package_name = package_match.group(1)
                break
        if package_name is None:
            raise ValueError(f"Cannot discover application package for {service}")
        if not (directory / "src" / package_name / "main.py").is_file():
            raise ValueError(f"Missing main.py for routed service {service}")
        services.append(
            ServiceDefinition(
                id=service,
                directory=directory,
                module=f"{package_name}.main",
                prefixes=prefixes,
            )
        )
    if not services:
        raise ValueError("No routed FlashMarket API services were discovered")
    return sorted(services, key=lambda service: service.id)


def _export_one(root: Path, service: ServiceDefinition, output: Path) -> None:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required to export service OpenAPI documents")
    exporter = root / "tools" / "openapi" / "export_service.py"
    command = [
        uv,
        "run",
        "--frozen",
        "python",
        str(exporter),
        "--module",
        service.module,
        "--service",
        service.id,
        "--output",
        str(output),
    ]
    completed = subprocess.run(
        command,
        cwd=service.directory,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(f"OpenAPI export failed for {service.id}:\n{details}")


def export_documents(root: Path, services: list[ServiceDefinition]) -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    with tempfile.TemporaryDirectory(prefix="flashmarket-openapi-") as temporary:
        output_directory = Path(temporary)
        with ThreadPoolExecutor(max_workers=min(4, len(services))) as executor:
            futures = {
                executor.submit(_export_one, root, service, output_directory / f"{service.id}.json"): service
                for service in services
            }
            for future in as_completed(futures):
                service = futures[future]
                future.result()
                document = json.loads(
                    (output_directory / f"{service.id}.json").read_text(encoding="utf-8")
                )
                if not isinstance(document, dict):
                    raise TypeError(f"OpenAPI document for {service.id} is not an object")
                documents[service.id] = document
    return documents


def _path_matches(path: str, prefix: str) -> bool:
    normalized = prefix.rstrip("/") or "/"
    return path == normalized or path.startswith(normalized + "/")


def _pascal(value: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[^A-Za-z0-9]+", value) if part)


def _walk(value: Any) -> Iterator[Any]:
    yield value
    if isinstance(value, dict):
        for nested in value.values():
            yield from _walk(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _walk(nested)


def _rewrite_refs(value: Any, rename: dict[str, str]) -> Any:
    if isinstance(value, dict):
        rewritten: dict[str, Any] = {}
        for key, nested in value.items():
            if key == "$ref" and isinstance(nested, str):
                rewritten[key] = rename.get(nested, nested)
            elif key == "security" and isinstance(nested, list):
                rewritten[key] = [
                    {
                        ("bearerAuth" if scheme == "HTTPBearer" else scheme): scopes
                        for scheme, scopes in requirement.items()
                    }
                    for requirement in nested
                ]
            else:
                rewritten[key] = _rewrite_refs(nested, rename)
        return rewritten
    if isinstance(value, list):
        return [_rewrite_refs(nested, rename) for nested in value]
    return value


def namespace_document(document: dict[str, Any], service: str) -> dict[str, Any]:
    """Namespace reusable components and normalize the bearer scheme."""
    result = copy.deepcopy(document)
    components = result.get("components", {})
    renamed_components: dict[str, dict[str, Any]] = {}
    refs: dict[str, str] = {}
    namespace = _pascal(service)

    for section, entries in components.items():
        if not isinstance(entries, dict):
            continue
        target: dict[str, Any] = {}
        for name, component in entries.items():
            if section == "securitySchemes" and name == "HTTPBearer":
                new_name = "bearerAuth"
            else:
                new_name = f"{namespace}{name}"
            target[new_name] = component
            refs[f"#/components/{section}/{name}"] = f"#/components/{section}/{new_name}"
        renamed_components[section] = target
    result["components"] = renamed_components
    return _rewrite_refs(result, refs)


def merge_documents(
    services: list[ServiceDefinition],
    documents: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    merged: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": "FlashMarket Public API",
            "version": "1.0.0",
            "description": "Same-origin public API contract for the FlashMarket platform.",
        },
        "servers": [{"url": "/", "description": "Current FlashMarket domain"}],
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
            },
        },
        "tags": [],
    }
    service_items: list[dict[str, Any]] = []

    for service in services:
        source = namespace_document(documents[service.id], service.id)
        operation_count = 0
        access_levels: set[str] = set()
        service_tags: set[str] = set()
        for path, path_item in sorted(source.get("paths", {}).items()):
            if not any(_path_matches(path, prefix) for prefix in service.prefixes):
                continue
            if path.startswith(EXCLUDED_PREFIXES):
                continue
            if not isinstance(path_item, dict):
                continue
            target_path = merged["paths"].setdefault(path, {})
            for method in HTTP_METHODS:
                operation = path_item.get(method)
                if not isinstance(operation, dict):
                    continue
                if method in target_path:
                    owner = target_path[method].get("x-flashmarket-service", "unknown")
                    raise ValueError(
                        f"Duplicate operation {method.upper()} {path}: {owner} and {service.id}"
                    )
                access = operation.get("x-flashmarket-access")
                if access not in ACCESS_LEVELS:
                    raise ValueError(
                        f"Unclassified access for {service.id} {method.upper()} {path}"
                    )
                operation["x-flashmarket-service"] = service.id
                if access == "anonymous":
                    operation["security"] = []
                elif not operation.get("security"):
                    operation["security"] = [{"bearerAuth": []}]
                operation_tags = operation.get("tags", [])
                service_tags.update(str(tag) for tag in operation_tags)
                access_levels.add(access)
                target_path[method] = operation
                operation_count += 1
            for shared_key in ("parameters", "summary", "description"):
                if shared_key in path_item and shared_key not in target_path:
                    target_path[shared_key] = path_item[shared_key]

        for section, entries in source.get("components", {}).items():
            if not isinstance(entries, dict):
                continue
            target = merged["components"].setdefault(section, {})
            for name, component in entries.items():
                if section == "securitySchemes" and name == "bearerAuth":
                    continue
                if name in target and target[name] != component:
                    raise ValueError(f"Conflicting component {section}.{name}")
                target[name] = component

        title = str(source.get("info", {}).get("title") or service.id.title())
        service_items.append(
            {
                "id": service.id,
                "name": title.removeprefix("FlashMarket "),
                "title": title,
                "prefixes": list(service.prefixes),
                "operationCount": operation_count,
                "accessLevels": sorted(access_levels),
                "tags": sorted(service_tags),
                "statusUrl": f"/dev/status/{service.id}",
            }
        )
        merged["tags"].append(
            {"name": service.id, "description": f"Operations owned by {title}."}
        )

    metadata = {
        "version": merged["info"]["version"],
        "openapi": merged["openapi"],
        "serviceCount": len(service_items),
        "operationCount": sum(item["operationCount"] for item in service_items),
        "services": service_items,
    }
    validate_merged_document(merged)
    return merged, metadata


def validate_merged_document(document: dict[str, Any]) -> None:
    if not str(document.get("openapi", "")).startswith("3.1."):
        raise ValueError("Merged document must use OpenAPI 3.1")
    paths = document.get("paths")
    if not isinstance(paths, dict) or not paths:
        raise ValueError("Merged document has no paths")
    components = document.get("components", {})
    for value in _walk(document):
        if not isinstance(value, dict):
            continue
        ref = value.get("$ref")
        if not isinstance(ref, str) or not ref.startswith("#/components/"):
            continue
        parts = ref.split("/")
        if len(parts) != 4 or parts[2] not in components or parts[3] not in components[parts[2]]:
            raise ValueError(f"Unresolved local reference: {ref}")
    for path in paths:
        if path.startswith(EXCLUDED_PREFIXES):
            raise ValueError(f"Operational or internal path leaked into contract: {path}")


def generate(root: Path, output_directory: Path) -> tuple[Path, Path]:
    gateway_path = root / "gateway" / "nginx.conf"
    routes = discover_gateway_routes(gateway_path.read_text(encoding="utf-8"))
    services = discover_services(root, routes)
    documents = export_documents(root, services)
    openapi, metadata = merge_documents(services, documents)

    output_directory.mkdir(parents=True, exist_ok=True)
    openapi_path = output_directory / "openapi.json"
    services_path = output_directory / "services.json"
    openapi_path.write_text(
        json.dumps(openapi, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    services_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return openapi_path, services_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = (args.output or root / "frontend" / "public" / "dev").resolve()
    openapi_path, services_path = generate(root, output)
    print(f"Generated {openapi_path}")
    print(f"Generated {services_path}")


if __name__ == "__main__":
    main()
