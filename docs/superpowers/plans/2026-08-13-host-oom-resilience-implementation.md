# Host OOM Resilience Implementation Plan

**Design:** `docs/superpowers/specs/2026-08-13-host-oom-resilience-design.md`

## 1. Resource-control contract

- Add a repository test that loads every deploy Compose file.
- Define explicit exemptions for one-shot key generation and migration jobs.
- Require memory limit, memory reservation, PID limit, init, graceful stop,
  restart policy, and bounded `json-file` logging on every long-running service.
- Check that resource values are positive and reservations do not exceed limits.

## 2. Compose resource classes

- Add reusable YAML anchors to each service deploy Compose file.
- Apply critical API, standard API, Media API, event-worker, maintenance-worker,
  service-nginx, Gateway, frontend, and exporter budgets from the approved design.
- Mirror the controls in local service Compose files so the root extended stack
  inherits them.
- Document environment overrides in the service environment examples.

## 3. Auth password bulkhead

- Introduce typed capacity settings and a stable capacity exception.
- Add an async gate that acquires with a timeout and always releases its permit.
- Route every request-path Argon2 operation through the gate while leaving CLI
  administration synchronous.
- Map exhausted capacity to HTTP 503 using the existing error contract.
- Test concurrency, timeout, success, failure, and cancellation behaviour.

## 4. Media validation bulkhead

- Introduce typed validation capacity settings and a stable domain exception.
- Guard the combined S3 read and image-validation phase with a timed async gate.
- Keep metadata, presigning, listing, and deletion outside the gate.
- Map exhaustion to HTTP 503 through the existing Media error handler.
- Test concurrency and permit release on all exit paths.

## 5. Bounded database pools

- Add shared process-role handling in the Docker entrypoint.
- Add service-prefixed API/worker pool settings to all nine services.
- Build PostgreSQL engines with role-specific size and overflow limits plus pool
  timeout and recycle values; avoid incompatible options for SQLite tests.
- Add focused tests for option selection and calculate the aggregate default cap.

## 6. Operations runbook

- Document exact commands to collect baselines, create persistent 2 GiB swap,
  set swappiness, render Compose, roll out groups, observe OOM/restart state, and
  roll back.
- Include recommended external observability/infrastructure limits and explicit
  checks before removing stale containers.
- Supply Prometheus alert-rule examples for memory availability, swap, high
  container utilization, restart growth, and OOM events.

## 7. Verification and delivery

- Run the repository contract tests and all affected service tests.
- Run Ruff on every changed Python file and Compose configuration rendering.
- Run frontend tests and production build to catch root-stack regressions.
- Confirm a clean diff, commit the implementation, and provide the production
  rollout commands without directly mutating the remote host.

