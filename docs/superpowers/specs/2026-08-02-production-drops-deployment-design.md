# Production Drops Deployment Design

## Problem

The production gateway routes `/api/v1/drops/*`, `/api/v1/admin/drops/*`, and
`/dev/status/drops` to `drops:8000`. The Drops workflow currently runs lint and
tests only; it neither publishes an image nor starts a production container.
Consequently, every Drops route returns `502 Bad Gateway`.

## Chosen approach

Extend the existing Drops workflow into the same immutable deployment pipeline
used by the other production services. A successful build publishes the Drops
image to GHCR and exposes its digest. Production always deploys that exact
digest, never a mutable tag.

The deployment owns three containers:

- `api`, exposed to the shared `shide-observability` network with the `drops`
  alias expected by the gateway;
- `scheduler`, which starts and ends scheduled drops;
- `outbox`, which publishes transactional outbox events to RabbitMQ.

No gateway route changes are required because the existing routes and health
mapping are correct.

## Configuration and dependencies

The workflow renders a mode-`0600` production environment file on the runner and
transfers it over SSH. It configures:

- PostgreSQL database `drops` on `shide-postgres`;
- a dedicated RabbitMQ vhost for Drops on `shide-rabbitmq`;
- the shared read-only Auth JWT public-key volume;
- production mode with debug and API documentation disabled;
- trusted hosts and CORS for the main gateway domain.

Deployment connection settings come from production variables, while SSH,
PostgreSQL, and RabbitMQ credentials come from GitHub secrets. The workflow
validates host, port, path, required credentials, and image digest before making
any remote change.

## Deployment sequence

1. Run the existing Drops tests.
2. Build and publish the image, recording its digest.
3. Upload the production Compose file and protected environment file.
4. Log the server into GHCR and pull the exact digest.
5. Run the image's `migrate` command. This also creates the Drops database and
   RabbitMQ vhost when absent.
6. Recreate `api`, `scheduler`, and `outbox` with orphan cleanup.
7. Wait for the API container healthcheck to become healthy; on failure, print
   bounded service logs and fail the deployment.
8. Verify `https://<gateway>/dev/status/drops` from the GitHub runner. A failed
   external check fails the deployment.

## Failure handling

Strict shell mode stops deployment on invalid configuration, failed migration,
image pull, unhealthy API, or failed gateway verification. Background workers
use `restart: unless-stopped`. Runtime containers are not started until the
migration succeeds. A previous image can be restored by rerunning a workflow or
tag that resolves to its known digest.

## Verification

Automated contract tests will assert that:

- the image digest is exported and consumed by the deployment;
- the deploy Compose file contains all three runtime services and the `drops`
  network alias;
- migrations run before the runtime containers start;
- the public gateway health route is checked;
- the production environment uses the expected database, messaging, JWT, and
  security settings.

Before rollout, the Drops suite, deployment contract tests, Compose rendering,
and Actionlint must pass. After rollout, `/dev/status/drops` must return `200`,
the public active-drops route must return an application response, and the admin
route without a token must return `401` or `403` rather than `502`.

## Out of scope

This change does not alter Drops domain behavior, API schemas, gateway routing,
or the administration UI. It only makes the already implemented service
available in production.
