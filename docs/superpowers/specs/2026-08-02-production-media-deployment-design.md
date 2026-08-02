# Production Media Deployment and Upload Routing

## Context

Production requests to `POST /api/v1/media/uploads` return `502 Bad Gateway`. The
public gateway and frontend are healthy, but `/dev/status/media` also returns 502,
proving that Nginx cannot reach its configured `media:8000` upstream.

The repository builds and publishes the Media image in `media-ci.yml`, and contains a
production Compose file, but has no Media deployment job. Consequently no production
container joins the shared network with the `media` alias. Even after deploying the API,
the browser still needs a TLS-enabled public object-storage endpoint for presigned
uploads.

## Goals

- Deploy the exact tested Media image digest to production on `main`, Media version
  tags, or manual workflow dispatch.
- Run database migrations before replacing the Media runtime.
- Start both the Media API and cleanup worker on the shared production network.
- Make browser uploads available through the existing HTTPS FlashMarket domain without
  a new DNS record, certificate, or MinIO-wide CORS change.
- Fail deployment when the API, storage dependency, or public gateway route is broken.
- Preserve direct-to-storage uploads: uploaded bytes must not pass through FastAPI.

## Deployment Workflow

The existing Media workflow gains an image digest output and a production deploy job.
The deploy job follows the established Auth/Catalog service pattern:

1. validate SSH target, deploy path, domain, and required secrets;
2. render a mode-0600 production environment file;
3. upload `media/docker-compose.deploy.yml` and the environment file;
4. authenticate the server to GHCR and pull the exact image digest;
5. run Media database migrations as a one-shot container;
6. recreate `api` and `cleanup` without building on the server;
7. wait for the API health check and show logs on failure;
8. verify the internal API and the public same-origin gateway status route.

The production environment includes PostgreSQL, MinIO credentials, internal/public S3
endpoints, public media base URL, JWT verification settings, trusted hosts, CORS origins,
cleanup settings, and explicit production hardening flags. Secret values are never
printed or copied into repository files.

## Same-Origin Storage Route

The main production gateway exposes `/media-storage/` on the existing
`https://flashmarket.shide.world` origin. Requests are streamed to
`http://shide-minio:9000` with the `/media-storage` prefix removed while preserving the
remaining bucket/object path and query string.

The route has a 30 MiB request limit, disabled request buffering, five-minute
send/read timeouts, and no application JWT or CSRF headers. Because frontend and storage
share the same HTTPS origin, browser CORS configuration is not required for this route.
The ordinary JSON API keeps its existing small body-size limit.

Production Media signs presigned POSTs with:

- `MEDIA_S3_INTERNAL_ENDPOINT=http://shide-minio:9000` for server-side validation;
- `MEDIA_S3_PUBLIC_ENDPOINT=https://flashmarket.shide.world/media-storage` for browser
  uploads;
- `MEDIA_PUBLIC_BASE_URL=https://flashmarket.shide.world/media-storage/flashmarket-public`
  for stable public reads.

Botocore must retain the configured endpoint prefix in generated presigned form URLs.
An integration test proves this contract through a local Nginx/MinIO route before
production rollout.

## Security and Failure Handling

- The gateway storage route exposes only MinIO's S3 API; write authorization remains a
  short-lived presigned policy issued to an authenticated user.
- Bucket listing stays denied and anonymous access remains read-only.
- Media production validation rejects default credentials, HTTP public URLs, enabled
  docs/debug, and unsafe database/storage transport unless the existing explicit
  internal-service exception is configured.
- Failed migrations stop deployment before runtime replacement.
- An unhealthy API prevents a successful deploy and emits bounded service logs.
- The cleanup worker removes abandoned pending uploads through the existing lifecycle.
- Public verification checks `/dev/status/media` so a missing Docker alias cannot ship
  unnoticed again.

## Verification

- YAML parsing and workflow contract tests confirm the digest output, deploy gate,
  migration command, API/cleanup startup, and required environment variables.
- Docker Compose renders the production gateway and Media files successfully.
- Gateway routing tests confirm prefix stripping, streaming, size limit, and timeouts.
- A presigned POST through the prefixed storage endpoint succeeds, then HEAD/read/delete
  succeed through the internal endpoint.
- Media unit/API suites and frontend upload tests pass.
- After rollout, `https://flashmarket.shide.world/dev/status/media` returns 200 and an
  authenticated real upload reaches `READY` with a loadable public URL.

## Rollout

Deploy Media first so the existing gateway upstream becomes reachable. Deploy the
gateway route next, then update Media's public endpoint values and redeploy Media if the
route was not already available during the first deployment. The workflow's final
verification must confirm both API readiness and the gateway status route. Rollback uses
the previous image digest and leaves stored objects/database migrations forward
compatible.

## Acceptance Criteria

- `/api/v1/media/uploads` no longer returns 502 in production.
- Production runs healthy Media API and cleanup containers using an immutable digest.
- Presigned upload URLs use the public HTTPS `/media-storage` endpoint and never expose
  Docker hostnames or raw MinIO ports.
- A real file upload completes and its public URL loads through the main domain.
- Future Media changes deploy automatically with the same health and routing checks.
