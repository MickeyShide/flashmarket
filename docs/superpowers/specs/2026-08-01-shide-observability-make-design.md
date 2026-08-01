# FlashMarket Local Stack Make Workflow

## Goal

Provide one root command, `make up`, that builds and starts the complete
FlashMarket development stack while connecting it to an already-running local
`shide-observability` stack.

FlashMarket must not start, stop, or otherwise manage the neighbouring
`shide-observability` project.

## Existing Integration Contract

The root Compose project already connects FlashMarket services to the external
Docker network named `shide-observability`. Application services use the shared
PostgreSQL, Redis, RabbitMQ, and MinIO containers through their stable Docker
DNS names. Services also mount the external `shide-backend-logs-local` volume so
Promtail can collect their logs. API container entrypoints create their required
databases and RabbitMQ vhosts and apply Alembic migrations before starting.

The Make workflow will preserve this contract instead of duplicating
infrastructure or migration logic.

## Command Interface

The root `Makefile` will expose these commands:

- `make up`: validate prerequisites, build images, start FlashMarket in the
  background, and wait for services to reach their Compose running/healthy
  state.
- `make down`: stop and remove only the FlashMarket Compose project. Shared
  observability containers, network, volume, and data remain untouched.
- `make restart`: run `down`, then `up`.
- `make logs`: follow recent logs for the FlashMarket Compose project.
- `make ps`: show FlashMarket service state.
- Existing test and OpenAPI targets remain available and unchanged.

`make up` is the single happy-path command. It will invoke the checks itself;
users do not need to run an initialization command first.

## Preflight Checks

Before invoking `docker compose up`, the workflow will fail fast unless all of
the following are true:

1. Docker CLI is available.
2. Docker Compose is available through `docker compose`.
3. The Docker daemon is reachable.
4. The external Docker network `shide-observability` exists.
5. The external volume `shide-backend-logs-local` exists.
6. The shared infrastructure containers required by FlashMarket are running:
   `shide-postgres`, `shide-redis`, `shide-rabbitmq`, and `shide-minio`.

Where a required infrastructure container defines a Docker health check, its
state must be `healthy`; otherwise `running` is sufficient. Observability-only
containers such as Grafana, Prometheus, Loki, and Promtail are not application
startup dependencies and are therefore not a hard gate.

Each failed check will print a concise explanation that the local
`shide-observability` stack must be started separately. The check will not
create missing Docker resources and will not depend on the neighbouring
repository's filesystem path.

## Startup and Failure Behaviour

After preflight succeeds, `make up` will run the root Compose project with image
building, detached mode, and Compose readiness waiting enabled. Compose remains
the source of truth for service dependencies and health checks.

If startup fails, the target returns a non-zero exit code and prints the current
FlashMarket Compose service state to make the failing container visible. It
does not tear down successfully started containers automatically, preserving
their logs for diagnosis.

`make down` is scoped to the FlashMarket Compose project and must never use
flags that remove external volumes or unrelated containers.

## Portability

The Makefile will support its current Windows PowerShell environment and a
POSIX shell environment. Platform-specific preflight syntax may differ, but
command names, validation semantics, and error messages will remain equivalent.
No absolute path to either repository will be embedded.

## Verification

Implementation verification will cover:

- Makefile dry-run inspection for the public targets.
- Successful Compose configuration resolution.
- Failure of the observability preflight when a required external resource or
  container is unavailable, without creating or changing that resource.
- Successful preflight against a running local `shide-observability` stack.
- `make up` reaching running/healthy state for FlashMarket and `make ps`
  reporting its services.
- `make down` leaving the shared observability containers, network, volume, and
  persistent data intact.

