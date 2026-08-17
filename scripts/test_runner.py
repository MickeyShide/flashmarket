"""Cross-platform test runner used by the repository Makefile."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Sequence
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SERVICE_NAMES = (
    "auth",
    "catalog",
    "inventory",
    "orders",
    "payments",
    "notifications",
    "wishlist",
    "drops",
    "media",
)
SPECIAL_SUITES = ("jwt", "gateway", "celery")
CRITICAL_SERVICES = (
    "gateway",
    "catalog",
    "auth",
    "inventory",
    "orders",
    "payments",
    "notifications",
    "orders-outbox",
    "payments-consumer",
    "payments-outbox",
    "orders-consumer",
    "inventory-consumer",
    "inventory-outbox",
    "notifications-consumer",
)
ADMIN_PASSWORD = "SagaAdminPassword123!"
S3_ACCESS_KEY = "shide"
S3_SECRET_KEY = "shide-e2e-secret"


def announce(message: str) -> None:
    """Print a visible phase heading."""
    print(f"\n==> {message}", flush=True)


def run_command(
    command: Sequence[str],
    *,
    cwd: Path = PROJECT_ROOT,
    env: dict[str, str] | None = None,
    check: bool = True,
    capture: bool = False,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess without shell-specific command syntax."""
    result = subprocess.run(
        list(command),
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        capture_output=capture,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        if capture:
            if result.stdout:
                print(result.stdout, file=sys.stdout, end="", flush=True)
            if result.stderr:
                print(result.stderr, file=sys.stderr, end="", flush=True)
        raise subprocess.CalledProcessError(
            result.returncode,
            list(command),
            output=result.stdout,
            stderr=result.stderr,
        )
    return result


def require_executable(name: str) -> None:
    """Fail with a useful message when a required CLI is unavailable."""
    if shutil.which(name) is None:
        raise RuntimeError(f"Required executable {name!r} was not found on PATH")


def run_service_suite(service: str) -> None:
    """Run one service or repository-level test suite."""
    if service in SERVICE_NAMES:
        announce(f"{service} test suite")
        run_command(("uv", "run", "pytest"), cwd=PROJECT_ROOT / service)
        return

    if service == "jwt":
        announce("shared JWT verifier test suite")
        run_command(
            (
                "uv",
                "run",
                "--project",
                "shared/jwt_verifier",
                "pytest",
                "shared/jwt_verifier/tests",
                "-q",
            )
        )
        return

    if service == "gateway":
        announce("Gateway routing test suite")
        run_command(
            (
                "uv",
                "run",
                "--with",
                "pytest,pytest-asyncio,httpx,aio-pika",
                "pytest",
                "tests/test_gateway_routing.py",
                "-q",
            )
        )
        return

    if service == "celery":
        announce("shared Celery runtime test suite")
        run_command(
            (
                "uv",
                "run",
                "--project",
                "shared/celery_runtime",
                "pytest",
                "shared/celery_runtime/tests",
                "-q",
            )
        )
        return

    supported = ", ".join((*SERVICE_NAMES, *SPECIAL_SUITES))
    raise ValueError(f"Unknown service {service!r}. Supported values: {supported}")


def run_fast_tests() -> None:
    """Run every test suite that does not require Docker orchestration."""
    require_executable("uv")
    for service in (*SERVICE_NAMES, *SPECIAL_SUITES):
        run_service_suite(service)


class E2ERunner:
    """Own an isolated Purchase Saga Docker environment."""

    def __init__(self) -> None:
        suffix = uuid.uuid4().hex[:10]
        self.project = f"flashmarket-e2e-{suffix}"
        self.network = f"{self.project}-network"
        self.log_volume = f"{self.project}-logs"
        self.postgres = f"{self.project}-postgres"
        self.redis = f"{self.project}-redis"
        self.rabbitmq = f"{self.project}-rabbitmq"
        self.minio = f"{self.project}-minio"
        self.gateway = f"{self.project}-gateway"
        self.gateway_exporter = f"{self.project}-gateway-exporter"
        self.admin_email = f"saga-admin-{suffix}@example.com"
        self.override_path: Path | None = None
        self.compose_env = os.environ.copy()
        self.compose_env.update(
            {
                "E2E_NETWORK": self.network,
                "E2E_LOG_VOLUME": self.log_volume,
                "E2E_GATEWAY_CONTAINER": self.gateway,
                "E2E_GATEWAY_EXPORTER_CONTAINER": self.gateway_exporter,
                "S3_ACCESS_KEY": S3_ACCESS_KEY,
                "S3_SECRET_KEY": S3_SECRET_KEY,
            }
        )

    def compose_command(self, *arguments: str) -> tuple[str, ...]:
        """Build a Docker Compose command for this isolated project."""
        if self.override_path is None:
            raise RuntimeError("E2E Compose override has not been created")
        return (
            "docker",
            "compose",
            "-p",
            self.project,
            "-f",
            "docker-compose.yml",
            "-f",
            str(self.override_path),
            *arguments,
        )

    def compose(
        self,
        *arguments: str,
        check: bool = True,
        capture: bool = False,
        timeout: float | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run Docker Compose for this E2E project."""
        return run_command(
            self.compose_command(*arguments),
            env=self.compose_env,
            check=check,
            capture=capture,
            timeout=timeout,
        )

    def write_override(self, directory: Path) -> None:
        """Create the temporary Compose overrides needed for isolation."""
        self.override_path = directory / "docker-compose.e2e.yml"
        services_without_host_ports = (
            "auth",
            "catalog",
            "inventory",
            "orders",
            "payments",
            "notifications",
            "wishlist",
            "drops",
            "media",
            "frontend",
        )
        service_overrides = "\n".join(
            (
                f"  {service}:\n"
                "    ports: !reset []\n"
                "    healthcheck:\n"
                "      timeout: 15s"
            )
            for service in services_without_host_ports
        )
        worker_health_overrides = "\n".join(
            f"  {service}:\n    healthcheck:\n      timeout: 15s"
            for service in CRITICAL_SERVICES
            if service not in services_without_host_ports and service != "gateway"
        )
        content = f"""services:
{service_overrides}
{worker_health_overrides}
  gateway:
    container_name: ${{E2E_GATEWAY_CONTAINER}}
    ports: !override
      - target: 80
        published: \"0\"
        host_ip: 127.0.0.1
        protocol: tcp
  gateway-exporter:
    container_name: ${{E2E_GATEWAY_EXPORTER_CONTAINER}}

networks:
  default:
    name: ${{E2E_NETWORK}}
    external: true
  shide-observability:
    name: ${{E2E_NETWORK}}
    external: true

volumes:
  backend-logs-local:
    name: ${{E2E_LOG_VOLUME}}
    external: true
"""
        self.override_path.write_text(content, encoding="utf-8")

    def create_infrastructure(self) -> None:
        """Start isolated PostgreSQL, Redis, and RabbitMQ containers."""
        announce("Creating isolated E2E infrastructure")
        run_command(("docker", "network", "create", self.network))
        run_command(("docker", "volume", "create", self.log_volume))
        run_command(
            (
                "docker",
                "run",
                "--rm",
                "--volume",
                f"{self.log_volume}:/var/log/shide",
                "alpine:3.21",
                "chmod",
                "0777",
                "/var/log/shide",
            )
        )
        run_command(
            (
                "docker",
                "run",
                "-d",
                "--name",
                self.postgres,
                "--network",
                self.network,
                "--network-alias",
                "shide-postgres",
                "-e",
                "POSTGRES_USER=shide",
                "-e",
                "POSTGRES_PASSWORD=shide",
                "-e",
                "POSTGRES_DB=postgres",
                "postgres:17-alpine",
            )
        )
        run_command(
            (
                "docker",
                "run",
                "-d",
                "--name",
                self.redis,
                "--network",
                self.network,
                "--network-alias",
                "shide-redis",
                "redis:7-alpine",
            )
        )
        run_command(
            (
                "docker",
                "run",
                "-d",
                "--name",
                self.rabbitmq,
                "--network",
                self.network,
                "--network-alias",
                "shide-rabbitmq",
                "-e",
                "RABBITMQ_DEFAULT_USER=shide",
                "-e",
                "RABBITMQ_DEFAULT_PASS=shide",
                "-e",
                "RABBITMQ_DEFAULT_VHOST=flashmarket",
                "rabbitmq:3-management-alpine",
            )
        )
        run_command(
            (
                "docker",
                "run",
                "-d",
                "--name",
                self.minio,
                "--network",
                self.network,
                "--network-alias",
                "shide-minio",
                "-e",
                f"MINIO_ROOT_USER={S3_ACCESS_KEY}",
                "-e",
                f"MINIO_ROOT_PASSWORD={S3_SECRET_KEY}",
                "minio/minio:RELEASE.2025-04-22T22-12-26Z",
                "server",
                "/data",
            )
        )

        self.wait_for_command(
            ("docker", "exec", self.postgres, "pg_isready", "-U", "shide", "-q"),
            description="PostgreSQL",
            timeout=60,
        )
        for database in (
            "auth",
            "catalog",
            "inventory",
            "orders",
            "payments",
            "notifications",
            "wishlist",
            "drops",
            "media",
        ):
            run_command(
                (
                    "docker",
                    "exec",
                    self.postgres,
                    "psql",
                    "-U",
                    "shide",
                    "-d",
                    "postgres",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    f"CREATE DATABASE {database};",
                ),
                capture=True,
            )

        self.wait_for_command(
            ("docker", "exec", self.rabbitmq, "rabbitmqctl", "status"),
            description="RabbitMQ",
            timeout=90,
        )
        self.wait_for_command(
            (
                "docker",
                "exec",
                self.minio,
                "curl",
                "--fail",
                "--silent",
                "http://127.0.0.1:9000/minio/health/ready",
            ),
            description="MinIO",
            timeout=90,
        )
        run_command(
            (
                "docker",
                "run",
                "--rm",
                "--network",
                self.network,
                "-e",
                f"MC_HOST_e2e=http://{S3_ACCESS_KEY}:{S3_SECRET_KEY}@shide-minio:9000",
                "minio/mc:RELEASE.2025-04-16T18-13-26Z",
                "mb",
                "--ignore-existing",
                "e2e/flashmarket-public",
            )
        )
        for vhost in ("payments", "notifications"):
            run_command(
                ("docker", "exec", self.rabbitmq, "rabbitmqctl", "add_vhost", vhost),
                capture=True,
            )
            run_command(
                (
                    "docker",
                    "exec",
                    self.rabbitmq,
                    "rabbitmqctl",
                    "set_permissions",
                    "-p",
                    vhost,
                    "shide",
                    ".*",
                    ".*",
                    ".*",
                ),
                capture=True,
            )

    def wait_for_command(
        self,
        command: Sequence[str],
        *,
        description: str,
        timeout: float,
    ) -> None:
        """Poll a command until it succeeds or the deadline expires."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = run_command(command, check=False, capture=True)
            if result.returncode == 0:
                return
            time.sleep(1)
        raise TimeoutError(f"{description} did not become ready within {timeout:.0f}s")

    def start_stack(self) -> None:
        """Build and start the application stack, then verify service health."""
        announce("Building and starting the isolated application stack")
        self.compose("config", "--quiet", timeout=30)
        self.compose("build", "--quiet", timeout=900)
        self.compose("up", "-d", "--no-build", capture=True, timeout=300)

        deadline = time.monotonic() + 300
        pending = set(CRITICAL_SERVICES)
        while time.monotonic() < deadline:
            pending = {
                service
                for service in CRITICAL_SERVICES
                if self.service_health(service) != "healthy"
            }
            if not pending:
                announce("All critical services are healthy")
                return
            time.sleep(3)
        raise TimeoutError(
            "Services did not become healthy within 300s: " + ", ".join(sorted(pending))
        )

    def service_health(self, service: str) -> str:
        """Return the Docker health or runtime status for a Compose service."""
        container_result = self.compose("ps", "-q", service, check=False, capture=True)
        container = container_result.stdout.strip()
        if not container:
            return "missing"
        inspect_result = run_command(
            (
                "docker",
                "inspect",
                "--format",
                "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
                container,
            ),
            check=False,
            capture=True,
        )
        if inspect_result.returncode != 0:
            return "missing"
        return inspect_result.stdout.strip()

    def bootstrap_admin(self) -> None:
        """Create the administrator used by the E2E fixtures."""
        announce("Bootstrapping the E2E administrator")
        self.compose(
            "exec",
            "-T",
            "auth",
            ".venv/bin/python",
            "-m",
            "auth_service.cli",
            "create-admin",
            "--email",
            self.admin_email,
            "--password",
            ADMIN_PASSWORD,
            "--full-name",
            "Saga E2E Administrator",
            timeout=60,
        )

    def gateway_url(self) -> str:
        """Discover the random loopback port assigned to Gateway."""
        result = self.compose("port", "gateway", "80", capture=True)
        endpoint = result.stdout.strip().splitlines()[0]
        _, separator, port = endpoint.rpartition(":")
        if not separator or not port.isdigit():
            raise RuntimeError(f"Could not parse Gateway endpoint: {endpoint!r}")
        return f"http://127.0.0.1:{port}"

    def run_tests(self) -> None:
        """Run the authenticated Purchase Saga suite through Gateway."""
        gateway_url = self.gateway_url()
        announce(f"Running Purchase Saga E2E tests through {gateway_url}")
        test_env = os.environ.copy()
        test_env.update(
            {
                "FLASHMARKET_GATEWAY": gateway_url,
                "SAGA_ADMIN_EMAIL": self.admin_email,
                "SAGA_ADMIN_PASSWORD": ADMIN_PASSWORD,
            }
        )
        run_command(
            (
                "uv",
                "run",
                "--with",
                "pytest,pytest-asyncio,httpx,aio-pika",
                "pytest",
                "tests/test_purchase_saga.py",
                "-v",
                "-m",
                "integration",
            ),
            env=test_env,
            timeout=180,
        )

    def diagnostics(self) -> None:
        """Print service state and logs after an E2E failure."""
        if self.override_path is None:
            return
        announce("E2E diagnostics")
        self.compose("ps", "-a", check=False)
        for service in CRITICAL_SERVICES:
            print(f"\n--- {service} logs ---", flush=True)
            self.compose("logs", "--tail", "80", service, check=False)

    def cleanup(self) -> None:
        """Remove only resources bearing this runner's unique names."""
        announce("Cleaning isolated E2E resources")
        if self.override_path is not None:
            self.compose(
                "down",
                "-v",
                "--remove-orphans",
                check=False,
                capture=True,
                timeout=180,
            )
        for container in (self.postgres, self.redis, self.rabbitmq, self.minio):
            run_command(("docker", "rm", "-f", container), check=False, capture=True)
        run_command(
            ("docker", "volume", "rm", self.log_volume), check=False, capture=True
        )
        run_command(
            ("docker", "network", "rm", self.network), check=False, capture=True
        )


def run_e2e_tests() -> None:
    """Provision, test, diagnose, and clean one isolated E2E environment."""
    require_executable("uv")
    require_executable("docker")
    runner = E2ERunner()
    with tempfile.TemporaryDirectory(prefix="flashmarket-e2e-") as temp_directory:
        runner.write_override(Path(temp_directory))
        try:
            runner.create_infrastructure()
            runner.start_stack()
            runner.bootstrap_admin()
            runner.run_tests()
        except BaseException:
            runner.diagnostics()
            raise
        finally:
            runner.cleanup()


def print_help() -> None:
    """Print the Makefile-facing command reference."""
    print(
        """FlashMarket test commands:
  make test                         Run all non-Docker test suites
  make test-e2e                     Run isolated Purchase Saga E2E tests
  make test-all                     Run every test suite
  make test-service SERVICE=orders  Run one service, jwt, or gateway suite
  make help                         Show this help
"""
    )


def parse_args() -> argparse.Namespace:
    """Parse the runner command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("help")
    subparsers.add_parser("test")
    subparsers.add_parser("test-e2e")
    subparsers.add_parser("test-all")
    service_parser = subparsers.add_parser("test-service")
    service_parser.add_argument("--service", required=True)
    return parser.parse_args()


def main() -> int:
    """Dispatch the selected test command."""
    args = parse_args()
    try:
        if args.command == "help":
            print_help()
        elif args.command == "test":
            run_fast_tests()
        elif args.command == "test-e2e":
            run_e2e_tests()
        elif args.command == "test-all":
            run_fast_tests()
            run_e2e_tests()
        elif args.command == "test-service":
            require_executable("uv")
            run_service_suite(args.service)
    except (
        OSError,
        subprocess.SubprocessError,
        RuntimeError,
        TimeoutError,
        ValueError,
    ) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
