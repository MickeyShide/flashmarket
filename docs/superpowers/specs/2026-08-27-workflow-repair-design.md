# Workflow Repair Design

## Goal

Restore all GitHub Actions workflows to a healthy state without weakening production
readiness checks or hiding service failures behind retries and longer timeouts.

Success means:

- every workflow file passes GitHub Actions static validation;
- the latest known failures in Orders deploy, Wishlist deploy, Notifications deploy,
  and Purchase Saga E2E have a repository-side fix;
- deploy workflows keep immutable image digests, serialized production deployment,
  credential isolation, migration-before-runtime ordering, and strict health checks;
- existing workflow contract tests and related service tests pass.

## Observed Failures

The latest main-branch run at commit `070befc` had four failures:

1. Orders production deploy: the API became unhealthy because the runtime image did
   not contain `httpx`, although Orders imports it from `catalog_client.py`.
2. Purchase Saga E2E: Orders failed with the same missing runtime dependency. The
   E2E stack also started database-dependent workers concurrently with API migrations,
   producing avoidable missing-table errors during startup.
3. Wishlist production deploy: the outbox process stayed alive but did not create a
   fresh heartbeat before the deploy readiness deadline.
4. Notifications production deploy: consumer/outbox readiness was similarly unstable;
   workers only record an outbox heartbeat after a complete successful polling cycle.

Wishlist and Drops also use Node 20-based Action revisions and now emit runner
deprecation warnings.

## Chosen Design

### Runtime dependency correctness

Move `httpx` from Orders' development-only dependency group into the project's runtime
dependencies and refresh `orders/uv.lock`. Add a regression assertion that imports the
production application from an environment containing only runtime dependencies.

### Deterministic E2E startup

Keep the isolated Docker project and cleanup behavior. Split stack startup into two
phases:

1. build images and start the API services whose entrypoints apply migrations;
2. wait until those APIs are healthy, then start consumers, outbox workers, maintenance
   processes, Gateway, and Frontend.

This preserves the real production entrypoints while preventing workers from querying
schemas before migrations finish. Failure diagnostics continue to include container
state and bounded logs.

### Worker readiness

Outbox workers will use the shared periodic heartbeat context after RabbitMQ topology
has been established. This matches the existing consumer pattern: a worker is healthy
only after it has connected successfully, while the heartbeat remains fresh during
idle periods and asynchronous database or broker work.

The change applies consistently to all transactional outbox workers, not only the two
services that happened to fail in the latest run. Existing reconnect behavior remains
responsible for startup failures. Health checks remain strict and continue to fail when
the process exits, cannot establish its broker session, or stops scheduling the event
loop.

### Workflow consistency and diagnostics

- Upgrade remaining `actions/checkout@v4` and unpinned old `setup-uv` uses to the same
  supported revisions used by the other workflows.
- Preserve least-privilege permissions, immutable digests, SSH validation, per-service
  Docker credential directories, and the shared host deployment lock.
- Make deploy readiness helpers validate that a container ID exists and print its
  runtime state, health log, and service logs before failing. A failed `docker compose
  up` must also emit relevant service diagnostics.
- Do not convert failed readiness checks into warnings and do not extend deadlines as a
  substitute for fixing startup.

## Error Handling

- Missing containers fail immediately with a named GitHub annotation.
- Unhealthy containers report status, exit code, restart count, Docker health output,
  and bounded logs.
- E2E startup failures report the unhealthy phase and retain the existing isolated
  cleanup in `finally`.
- Registry credentials are removed by the existing remote trap even when deployment
  fails.

## Verification

1. Run `actionlint` against every file in `.github/workflows`.
2. Parse every workflow as YAML and verify all referenced local paths exist.
3. Run workflow/deployment contract tests under `tests/`.
4. Run Orders tests and an Orders production-dependency/import check.
5. Run outbox and heartbeat tests for every affected service plus shared reliability
   tests.
6. Run E2E runner isolation tests. A full Saga Docker run is required in CI because the
   local Docker daemon is unavailable in the current environment.

## Scope Boundaries

This repair does not change business behavior, production secrets, deployment targets,
or public APIs. It does not bypass health verification, manually alter the production
host, or trigger deployments from the local workspace.
