# FlashMarket Host OOM Resilience Design

**Date:** 2026-08-13  
**Status:** Approved design, awaiting implementation planning  
**Scope:** The four-GiB single-host production deployment

## Problem

The production host has 3.8 GiB of usable RAM, no swap, and roughly 2.6 GiB of
steady-state container memory use. About 1.5 GiB belongs to FlashMarket and
about 0.8 GiB to observability and shared infrastructure. Only about 600 MiB was
available in the captured incident snapshot.

No FlashMarket production container currently has a memory or process limit.
Consequently, a short-lived spike in one module can force the host kernel to
choose an arbitrary process to kill. Restart policies recover some individual
containers, but they do not protect PostgreSQL, RabbitMQ, Redis, or the purchase
path from host-wide memory exhaustion.

Two application operations deserve particular attention:

- Auth uses Argon2 with a 64 MiB memory cost per password calculation. The work
  runs in AnyIO worker threads and can execute concurrently.
- Media reads an uploaded object into memory and asks Pillow to decode it. A
  valid 40-megapixel image can require substantially more decoded memory than
  its compressed 10-15 MiB input.

This design protects the host first and preserves the purchase and data path
before non-critical workloads.

## Goals

- A runaway API or worker must hit its own cgroup limit before exhausting host
  memory.
- PostgreSQL, RabbitMQ, Redis, Gateway, Auth, Inventory, Orders, and Payments
  receive the largest safety margin.
- Expensive Auth and Media operations have explicit concurrency bulkheads.
- Application database processes cannot collectively create an unbounded surge
  of PostgreSQL connections.
- Restart loops cannot fill the host disk with Docker logs.
- A small swap area absorbs transient pressure but is not treated as capacity.
- CI prevents production Compose services from silently losing their resource
  controls.
- Operators have an exact, reversible rollout and verification procedure.

## Non-goals

- Migrating the deployment to Kubernetes or Docker Swarm.
- Horizontally scaling services.
- Redesigning RabbitMQ delivery, DLQ, or retry semantics. That is the next
  reliability package.
- Replacing the external observability stack. Its repository is not part of
  this workspace; this design supplies a runbook and recommended limits for it.
- Automatically removing unrelated containers from the host.

## Chosen Approach

Use four complementary controls:

1. Per-container cgroup memory and PID limits.
2. Bounded concurrency for memory-amplifying application work.
3. Explicit small SQLAlchemy pools.
4. Host swap, log rotation, monitoring, and an operator runbook.

Swap alone only postpones OOM. Container limits alone do not reserve breathing
room for the kernel. Application semaphores alone do not cover unknown leaks.
The controls therefore ship as one package.

## Resource Classes

Resource values are configuration defaults, not hidden constants. Compose uses
environment-variable interpolation so the operator can tune a single service
without rebuilding its image.

| Class | Services | Memory limit | Reservation | PID limit |
|---|---|---:|---:|---:|
| Critical API | Auth, Inventory, Orders, Payments | 256 MiB | 96 MiB | 128 |
| Standard API | Catalog, Notifications, Wishlist, Drops | 192 MiB | 72 MiB | 96 |
| Media API | Media | 384 MiB | 128 MiB | 128 |
| Event worker | consumers and outbox relays | 160 MiB | 56 MiB | 64 |
| Maintenance worker | expiry, scheduler, cleanup | 128 MiB | 40 MiB | 64 |
| Service nginx | per-service nginx sidecars | 32 MiB | 8 MiB | 32 |
| Gateway | main nginx | 64 MiB | 16 MiB | 64 |
| Frontend | static nginx | 48 MiB | 12 MiB | 32 |
| Exporter | nginx exporter | 48 MiB | 12 MiB | 32 |

Reservations communicate expected steady-state demand; limits contain abnormal
growth. The sum of hard limits may exceed physical RAM because they are ceilings,
not allocations. The steady-state reservations must remain compatible with the
host budget.

Each production service receives:

- `mem_limit` and `mem_reservation`;
- `pids_limit`;
- `init: true` for correct child reaping where the image can support it;
- `stop_grace_period` appropriate for API or worker shutdown;
- Docker `json-file` rotation with `max-size: 10m` and `max-file: 3`.

The package will not set `oom_kill_disable`. Preventing the kernel from killing
a capped container could deadlock the host. It also will not assign strongly
negative `oom_score_adj` values to application containers before the external
infrastructure stack is governed by the same policy.

## Host Budget and Priority

The target operating envelope is:

- keep at least 512 MiB normally available to the host and page cache;
- add a 2 GiB swap file as a transient shock absorber;
- set `vm.swappiness=10` so normal traffic stays in RAM;
- alert when available RAM stays below 512 MiB, swap use exceeds 512 MiB, a
  container crosses 85% of its limit, or any container is OOM-killed;
- keep PostgreSQL, RabbitMQ, and Redis limits outside this repository in the
  runbook because their Compose project is external.

Recommended external-infrastructure ceilings for the current host are:

| Component | Recommended limit |
|---|---:|
| PostgreSQL | 512 MiB |
| RabbitMQ | 384 MiB |
| Redis | 128 MiB |
| Prometheus | 384 MiB |
| Grafana | 256 MiB |
| Loki | 256 MiB |
| MinIO | 256 MiB |
| Remaining exporters/agents combined | 256 MiB |

These external values must be validated against live peaks before application.
Prometheus retention and RabbitMQ watermark configuration may need adjustment to
fit them. The runbook treats this as a separate operator action, not an automatic
repository deployment.

## Auth Bulkhead

Create a small, reusable async password-work gate in Auth. Every Argon2 hash,
verify, dummy verify, and rehash operation passes through it.

- Default concurrency: `2`.
- Configuration: `AUTH_PASSWORD_WORK_CONCURRENCY`, constrained to `1..8`.
- Acquire timeout: configurable, default five seconds.
- Timeout response: HTTP 503 with a stable `auth_capacity_exhausted` error,
  rather than queuing arbitrary numbers of 64 MiB jobs.
- CLI-only password work remains synchronous because it is not request
  concurrent.

The gate belongs in the application layer and wraps the existing `to_thread`
calls. Password hashing parameters do not change.

## Media Bulkhead

Media confirmation currently downloads and decodes an object in the API process.
Put the entire read-and-validate section behind a service-level async gate.

- Default concurrency: `1` on the four-GiB host.
- Configuration: `MEDIA_VALIDATION_CONCURRENCY`, constrained to `1..4`.
- Acquire timeout: configurable, default ten seconds.
- Timeout response: HTTP 503 with stable `media_capacity_exhausted` semantics.
- Existing compressed-size and pixel-count checks remain in force.

Only expensive object validation is serialized. Presigning, listing, metadata
reads, and deletion requests remain concurrent.

## Database Pool Bounds

Every service constructs its SQLAlchemy engine with explicit settings:

- API: `pool_size=3`, `max_overflow=2`, `pool_timeout=5`,
  `pool_recycle=1800`, and existing `pool_pre_ping=True`;
- background process: `pool_size=1`, `max_overflow=1`;
- configuration fields allow later tuning with service-specific environment
  prefixes.

Because API and worker commands import the same settings module, the entrypoint
sets a role variable such as `FLASHMARKET_PROCESS_ROLE=api|worker` before exec.
Engine construction chooses the correct bounded profile. Tests using SQLite do
not receive PostgreSQL-only pool arguments.

With the current process count, the default theoretical PostgreSQL peak falls
from roughly 300 connections to fewer than 80. PgBouncer remains a future
scaling improvement rather than a prerequisite for this package.

## Failure Behaviour

When a container reaches its memory limit, the expected failure boundary is that
container. Docker records `OOMKilled=true` and `restart: unless-stopped` starts a
fresh process. Other services retain their memory budget.

Readiness remains dependency-aware, while liveness only indicates a running
process. Background processes gain lightweight health checks in a later deploy
reliability package; this package adds OOM observability rather than redefining
message-worker health.

Swap use is an alert condition. Sustained swap or repeated container OOM events
mean the limit or workload must be corrected; operators must not normalize them
by continually increasing swap.

## Compose and Configuration Layout

To avoid repeating a large block in every service, each service Compose file
defines YAML extension anchors for its runtime class and logging policy. Services
merge the suitable anchor and retain environment overrides such as:

```text
AUTH_API_MEMORY_LIMIT=256m
AUTH_WORKER_MEMORY_LIMIT=160m
MEDIA_API_MEMORY_LIMIT=384m
```

Production deployment files and the root development stack use the same class
defaults. Development may override them through `.env`; resource controls are
not silently disabled.

Examples document all new settings. Production workflows render only settings
that must differ from defaults; they do not hard-code host-specific emergency
values.

## Testing

Add repository contract tests that parse every production Compose model and
assert:

- each long-running service has memory, reservation, PID, restart, and log
  rotation controls;
- resource values parse as positive sizes and reservation does not exceed limit;
- critical APIs do not receive a smaller limit than standard APIs;
- Media has the dedicated larger limit;
- one-shot migration/key-generation containers are explicitly exempted.

Add Auth tests for:

- no more than the configured number of password jobs execute concurrently;
- capacity timeout produces the stable application error;
- permit release occurs after success, failure, and cancellation.

Add Media tests for equivalent validation-gate behaviour. Add database tests for
role-based pool selection without attempting a real PostgreSQL connection.

Run all service unit tests, repository contract tests, Ruff on changed files,
frontend tests, and a production Compose render check. A controlled Linux smoke
test starts a deliberately memory-hungry disposable process inside a test
container and verifies only that container is OOM-killed; this test is documented
for staging and is not run on a developer workstation by default.

## Rollout

1. Record 24-hour peak memory for every running container if available.
2. Remove or stop unrelated stale containers only after the operator confirms
   they are unused.
3. Create and persist the 2 GiB swap file using the runbook.
4. Deploy logging and resource limits to non-critical/maintenance workers first.
5. Deploy APIs and event workers one service at a time.
6. Observe memory, swap, restart count, readiness, and OOM status for at least
   ten minutes after each group.
7. Apply validated limits to the external infrastructure stack.
8. Exercise login, media validation, and the purchase saga.

Rollback consists of restoring the previous Compose files and redeploying. Swap
can remain enabled safely; removing it is a separate explicit operator action.

## Acceptance Criteria

- Every long-running FlashMarket production container has enforceable resource
  and log limits.
- A deliberately over-limit disposable workload cannot take down the host or
  unrelated service containers.
- Two concurrent Auth password operations succeed; excess work fails within the
  configured timeout without creating another Argon2 job.
- Only the configured number of Media validations can decode images concurrently.
- Default aggregate PostgreSQL connection capacity stays below 80.
- Host reports a 2 GiB persistent swap file and `vm.swappiness=10` after the
  operator follows the runbook.
- Alerts or documented Prometheus rules cover low available memory, swap use,
  high container memory, restart growth, and OOM kills.
- Existing service, contract, and frontend tests remain green.

