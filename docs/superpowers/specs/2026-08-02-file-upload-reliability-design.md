# Reliable File Uploads

## Context

FlashMarket creates Media upload sessions through the same-origin API and then sends
the file directly to a presigned S3-compatible POST URL. The shared frontend helper is
used by avatars, product images, brand logos, drop images, notification attachments,
and general public assets.

The upload-session request currently succeeds, but the browser cannot complete the
storage POST in the local stack for two independent reasons:

1. Media signs `http://localhost:9000`, while the shared MinIO container does not
   publish port 9000 to the host.
2. The browser-visible storage endpoint does not return CORS permission for the local
   storefront origins, so the browser cannot read the upload response.

The fix must cover every caller of the shared upload helper, work from both supported
local entry points, preserve direct-to-object-storage uploads, and retain a deployable
production configuration.

## Goals

- Make every existing upload purpose work through the common three-step flow:
  create session, upload to storage, complete session.
- Support the local storefront at `localhost` and `127.0.0.1`, on ports 3000 and 8080.
- Keep FastAPI out of the uploaded-byte data path.
- Keep local CORS scoped to FlashMarket without mutating the shared MinIO cluster.
- Keep production storage endpoints and allowed web origins explicit and configurable.
- Return a useful frontend error when storage is unreachable or blocks browser access.

## Non-goals

- Changing the existing per-purpose file types or size limits.
- Adding multipart/chunked S3 uploads.
- Moving ownership of the shared MinIO container into FlashMarket.
- Replacing presigned POSTs with uploads proxied by the Media API.

## Chosen Approach

Preserve direct S3-compatible uploads. The existing gateway container will expose a
second local listener on host port 9000 and stream storage traffic to the external
`shide-minio` container. This supplies the browser-visible endpoint already used by
Media without creating a second proxy container or changing frontend URLs.

The local gateway listener owns CORS for the browser-visible proxy. This is required
because the installed MinIO Community release does not implement per-bucket
`PutBucketCors`, while changing its global CORS setting would affect every project that
shares the cluster.

Production continues to use `MEDIA_S3_PUBLIC_ENDPOINT` for the browser-visible storage
endpoint and `MEDIA_PUBLIC_BASE_URL` for stable reads. Production operators must apply
the repository CORS policy with their real web origins rather than the local origins.

## Components and Data Flow

### Local storage listener

The gateway publishes `127.0.0.1:9000` and has a dedicated Nginx server listening on
container port 9000. It proxies the request URI unchanged to `http://shide-minio:9000`,
preserves the browser-visible `Host` header required by signed storage requests, and
does not attach application authentication headers.

The listener allows the largest current policy (`public_asset`, 25 MiB) plus multipart
form overhead. Request buffering is disabled so the proxy streams files instead of
writing complete request bodies to temporary storage. Storage-specific timeouts are
longer than ordinary JSON API timeouts.

The listener is separate from the main gateway server so the main API retains its
small default request-body limit.

### Local storage CORS

The storage listener permits browser `POST`, `GET`, `HEAD`, and preflight `OPTIONS`
requests from these local origins:

- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `http://localhost:8080`
- `http://127.0.0.1:8080`

The listener permits request headers needed by S3-compatible presigned forms and exposes
`ETag` and request identifiers useful for diagnostics. It does not enable credentialed
browser requests; authorization remains the short-lived signed form.

Nginx reflects `Access-Control-Allow-Origin` only when the request origin matches the
explicit allowlist. MinIO-provided CORS headers are hidden at this local boundary to
avoid duplicate or broader responses. Recreating the FlashMarket gateway reapplies the
same policy without restarting or reconfiguring shared MinIO.

For production, the deployment example documents bucket CORS for S3-compatible
providers that implement it. MinIO Community deployments instead use the server-wide
`api cors_allow_origin` setting and must account for every tenant of that cluster. The
Media service does not mutate production storage configuration at application startup.

### Media service configuration

Local Media configuration keeps separate internal and public S3 endpoints:

- internal operations: `http://shide-minio:9000`;
- browser-visible signed uploads: `http://localhost:9000`;
- stable local reads: `http://localhost:9000/flashmarket-public`.

The Media API CORS list also includes both supported local hostnames and ports. Most
frontend API calls remain same-origin through the gateway, but the explicit list keeps
direct Vite development supported and prevents hostname-specific failures.

Production examples continue to require HTTPS for the public storage endpoint, public
read base URL, and storefront origins.

### Frontend upload helper

All upload controls continue to call `uploadMediaAsset`. The helper retains client-side
purpose/type/size validation, sends JWT only when creating and completing the Media
session, and sends the presigned multipart form without JWT, CSRF, or cookies.

When the storage `fetch` fails before an HTTP response is available, the helper reports
that the storage endpoint is unavailable or its CORS policy is invalid. Non-success
storage responses continue to include their HTTP status. No per-screen upload logic is
introduced.

## Error Handling and Recovery

- If session creation fails, no storage request is attempted.
- If the storage endpoint is unreachable or CORS blocks the response, the UI reports a
  storage configuration error and does not call completion.
- If storage returns a non-success status, the UI reports the status and does not call
  completion.
- An abandoned pending asset remains safe and is removed by the existing expiration
  cleanup worker.
- If completion rejects mismatched or unsafe bytes, the existing Media service removes
  the uploaded object and returns its stable domain error.

## Verification

Automated and local verification will cover:

1. Docker Compose renders successfully and Nginx accepts the updated configuration.
2. `localhost:9000` is reachable after `make up`.
3. CORS responses allow each supported local origin and omit permission for an unknown
   origin.
4. Preflight requests return the permitted methods and headers.
5. A real presigned POST through the published endpoint stores the object, followed by
   successful HEAD/read/delete operations.
6. The Media API lifecycle test still creates, completes, reads, and deletes assets.
7. Frontend tests cover storage network failures and unsuccessful HTTP responses.
8. Existing Media and gateway regression suites pass.

## Acceptance Criteria

- Uploads work from the local Vite URL and the gateway URL using either `localhost` or
  `127.0.0.1`.
- Avatar, product, brand, drop, notification, and public-asset upload controls all use
  the repaired common path.
- Successful uploads reach `READY` and return a browser-loadable `public_url`.
- Restarting or recreating the FlashMarket stack retains working local storage CORS
  without mutating the shared MinIO configuration.
- Production configuration clearly specifies the public storage endpoint and exact
  storefront origins required for direct uploads.
- API body-size protection remains unchanged outside the dedicated storage listener.
