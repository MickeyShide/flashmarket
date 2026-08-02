# Production Wishlist Deployment Design

## Problem

Production requests to `/api/v1/wishlist` return `502 Bad Gateway`. The production host has no running Wishlist API or consumer containers, while the gateway routes Wishlist traffic to `http://wishlist:8000`. Local Wishlist containers are healthy and the same gateway routes work locally, so the application and route definitions are not the failure source.

The current Wishlist GitHub Actions workflow runs Ruff and pytest only. It does not build or publish an image and has no production deployment job. Consequently, a main-branch deployment cannot create a container with the `wishlist` network alias in the shared production network.

## Goal

Provide a repeatable production deployment for the Wishlist API and event consumer. A successful deployment must leave the API healthy, the consumer running, and the public gateway readiness endpoint returning HTTP 200.

## Chosen Approach

Extend the existing Wishlist workflow using the established Drops production deployment pattern:

1. Build an immutable Wishlist image and publish it to GHCR.
2. Deploy that exact image digest through SSH.
3. Render production configuration from GitHub environment variables and secrets.
4. Apply database migrations before replacing running services.
5. Start the API and consumer on the shared production Docker network.
6. Verify container health and public gateway reachability.

A manual server-only start is not the chosen solution because it is not reproducible and can disappear during later deployments. Removing the route is not acceptable because Wishlist is an active storefront feature.

## Production Compose

Add `wishlist/docker-compose.deploy.yml` with a project name dedicated to production Wishlist and two services:

- `api`, with the shared runtime environment, JWT public-key mount, stdout/stderr logging, health check, and network alias `wishlist`;
- `consumer`, using the same immutable image and environment but running `wishlist.event_consumer`.

Both services join the existing external `shide-observability` network. The API receives the `wishlist` alias required by the gateway. The compose file does not publish a host port because gateway-to-service traffic remains internal to Docker.

The JWT public-key volume is an external production resource. The API and consumer emit logs to stdout/stderr so Docker and Promtail can collect them without granting the unprivileged application user write access to a shared host volume. Both services use restart policies suitable for long-running services. The image is supplied through `WISHLIST_IMAGE`; local image names and `pull_policy: never` are not used in production.

## Image Build

Add an `image` job after pytest. It uses Buildx with `wishlist/Dockerfile`, GitHub Actions cache, GHCR authentication outside pull requests, and standard metadata tags for `develop`, `latest`, tags, pull requests, and commit SHAs.

The job exposes the content digest produced by the build action. Production deployment uses `ghcr.io/mickeyshide/flashmarket-wishlist@<digest>` so the deployed artifact is immutable and exactly matches the tested build.

## Deployment Configuration

The deploy job runs for manual dispatches, `main`, and `wishlist-v*` tags. It uses the protected `production` environment and validates:

- deployment host, port, user, and absolute deployment path;
- SSH private key presence;
- PostgreSQL and RabbitMQ secrets;
- gateway domain and infrastructure user formats;
- presence of the image digest.

When `WISHLIST_DEPLOY_PATH` is unset, the workflow uses `/home/<deploy-user>/flashmarket-wishlist`.

The rendered `.env` contains:

- the immutable image reference;
- `WISHLIST_ENVIRONMENT=production`;
- the production PostgreSQL URL for the `wishlist` database;
- the production RabbitMQ URL and vhost already expected by the service;
- CORS origins for the public gateway;
- trusted hosts for the main domain, Wishlist subdomain, internal aliases, and loopback health checks;
- the public JWT key directory, algorithm, issuer, and audience;
- production debug/docs settings;
- the existing internal-service security setting required by the current deployment topology.

Secrets are written to a runner temporary file with restrictive permissions, streamed to `.env.next` on the server, and atomically renamed to `.env`. Secret values are not printed.

## Remote Deployment Flow

The workflow uploads the production Compose file, logs the server into GHCR through stdin, and runs a bounded remote script with strict shell error handling.

The remote script:

1. validates the rendered Compose configuration;
2. pulls the exact image digest;
3. runs the service migration command with a fixed timeout;
4. starts or force-recreates the API and consumer without building on the host;
5. waits a bounded amount of time for the API health check;
6. fails immediately if the API becomes unhealthy or exits;
7. verifies that the consumer container is running;
8. prints final Compose state for deployment evidence;
9. logs out of GHCR through an exit trap.

All SSH, migration, health-wait, and overall remote deployment operations are bounded so a stalled host cannot consume an unbounded CI job.

## Public Verification

After the remote deployment succeeds, the workflow retries:

`https://<gateway-domain>/dev/status/wishlist`

The job succeeds only after the endpoint returns a successful HTTP response. This verifies the complete path: public TLS proxy, FlashMarket gateway, Docker DNS alias, Wishlist container, and readiness handler.

The root `/api/v1/wishlist` path is not used for verification because the service exposes resource-specific routes and legitimately returns 404 for the bare prefix.

## Error Handling and Recovery

If configuration validation, image pull, migration, API health, consumer state, or public verification fails, the workflow exits non-zero and includes bounded service logs where useful. Existing containers are not removed before the image and configuration are available. Database migration failure prevents service replacement.

The deployment is safe to rerun. Compose force-recreates the named services from the same desired configuration, migrations remain managed by the service's migration tooling, and records remain in the external PostgreSQL database.

## Tests

Add a repository-level deployment workflow test that asserts:

- workflow path filters include the deploy Compose file and its test;
- image build and digest output exist;
- deploy triggers cover manual dispatch, main, and Wishlist release tags;
- production secrets and variables are validated;
- the rendered environment includes database, RabbitMQ, JWT, CORS, and trusted-host settings;
- migrations run before service replacement;
- remote execution and migrations have explicit time bounds;
- API health and consumer running state are checked;
- the public gateway Wishlist readiness URL is verified;
- the deploy Compose file uses the immutable image variable, external network, `wishlist` alias, external key volume, stdout/stderr logging, API health check, and no host port.

Run the new workflow test, the Wishlist pytest suite, relevant gateway routing tests, Compose rendering, and YAML parsing before closure.

## Success Criteria

- A main-branch or manual Wishlist workflow publishes and deploys an immutable image.
- Production shows running Wishlist API and consumer containers.
- The API container becomes healthy and the consumer remains running.
- `https://flashmarket.shide.world/dev/status/wishlist` returns HTTP 200.
- Authenticated Wishlist create/list/delete requests no longer return gateway 502 responses.
- Deployment and regression tests pass.
