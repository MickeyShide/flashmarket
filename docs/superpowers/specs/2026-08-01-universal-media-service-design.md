# Universal Media Service Design

**Date:** 2026-08-01  
**Status:** Approved for specification  
**Scope:** Backend only

## 1. Summary

FlashMarket will gain a standalone `media` microservice for every public file that the
platform needs to retain: user avatars, product images, brand logos, review images,
drop images, notification attachments, and future public assets. The service owns file
metadata, upload authorization, S3 object keys, validation, stable public URLs,
eventual deletion, and orphan cleanup.

The service uses the S3-compatible MinIO installation that already belongs to the
external `shide-observability` infrastructure. FlashMarket must not start, initialize,
or persist its own MinIO instance. The `media` containers only join the existing
external `shide-observability` Docker network and receive bucket, endpoint, credentials,
and public base URL through environment variables.

The first release supports public assets only. Private documents, per-object download
authorization, antivirus scanning, CDN provisioning, image resizing, and frontend work
are explicitly outside this implementation.

## 2. Context and goals

Catalog currently stores product cover images, product image URLs, and brand logo URLs
as strings. There is no service that accepts uploads, verifies their contents, owns the
underlying objects, cleans abandoned uploads, or provides consistent authorization and
quotas. Other domains will require the same capability for avatars, reviews, drops, and
attachments.

The implementation must:

1. centralize public asset storage without coupling the service to Catalog or Auth
   persistence;
2. prevent FastAPI from becoming the data path for every uploaded byte;
3. keep object keys and public URLs stable and immutable;
4. authorize upload, binding, listing, and deletion through existing JWTs;
5. validate that uploaded bytes match the declared safe media type;
6. recover from abandoned uploads, retries, and temporary S3 failures;
7. use only the existing external MinIO/S3 infrastructure;
8. follow the repository's FastAPI, SQLAlchemy, Alembic, JWT, observability, Docker,
   typing, and testing conventions;
9. require no frontend changes;
10. avoid modifying the in-progress Inventory worktree changes.

## 3. Considered approaches

### 3.1 Presigned POST directly to S3 (selected)

The authenticated client first creates an upload session in Media. Media returns a
short-lived S3 presigned POST policy. The client sends the bytes directly to MinIO and
then asks Media to complete the upload. Completion verifies the stored object and
publishes its stable URL.

This avoids routing file bodies through the API, lets the S3 policy enforce object key,
declared MIME type, and size, and scales independently from the application containers.
It requires an explicit completion step and cleanup for abandoned sessions.

### 3.2 Multipart upload proxied through Media

This gives the client a simpler one-request contract and lets Media validate before
storage. It also doubles application network traffic, consumes API worker resources,
and turns Media into the bandwidth bottleneck. It is not selected.

### 3.3 S3 access in every domain service

Catalog, Auth, Reviews, and future services could each own their upload logic. This
duplicates credentials, policies, validation, quotas, key formats, cleanup, and S3
error handling. It is not selected.

## 4. Service boundaries

Media owns:

- upload-session creation and expiration;
- purpose-specific file policies;
- S3 object-key generation;
- presigned POST creation;
- metadata persistence;
- byte-level completion validation;
- SHA-256 calculation and image dimensions;
- public URL construction;
- asset-to-domain-entity bindings;
- ownership and role checks;
- public metadata reads;
- owner/admin upload history;
- eventual physical deletion;
- abandoned-object cleanup;
- S3 and database health reporting;
- Media-specific logs and metrics.

Media does not own:

- product, brand, user, review, or drop lifecycle;
- the choice of cover image or ordering of product images;
- Auth profile fields;
- cross-service validation that an arbitrary domain entity exists;
- frontend upload controls;
- a MinIO container, MinIO volume, bucket initialization, or infrastructure lifecycle;
- private files;
- CDN setup;
- image transformations or thumbnails;
- malware scanning of arbitrary executable/archive formats.

Catalog remains compatible because the resulting `public_url` can be stored in its
existing URL fields. Other domains may either store that URL or query Media by entity
binding. Media never writes directly to another service's database.

## 5. External infrastructure contract

The following resources are prerequisites owned outside this repository:

- external Docker network `shide-observability`;
- an S3-compatible endpoint reachable from that network, conventionally
  `http://shide-minio:9000` but always configurable;
- an existing bucket dedicated to FlashMarket public assets;
- credentials permitted to create, read, inspect, and delete objects in that bucket;
- a public endpoint/base URL through which browsers can upload and read objects;
- bucket CORS permitting the configured FlashMarket frontend origins to perform the
  presigned POST;
- public anonymous `GetObject` for asset keys, while anonymous bucket listing remains
  forbidden.

Media fails startup validation when required S3 settings are absent. Readiness returns
`503` when the bucket is unreachable or unavailable. Media never creates a bucket and
never changes the bucket policy or CORS rules.

Two endpoints are configured separately because Docker-internal DNS usually differs
from the browser-visible host:

- `MEDIA_S3_INTERNAL_ENDPOINT`: used by the API and cleanup worker for HEAD, GET, and
  DELETE operations;
- `MEDIA_S3_PUBLIC_ENDPOINT`: used solely when signing a browser-visible presigned POST;
- `MEDIA_PUBLIC_BASE_URL`: stable read base URL and later CDN cutover point.

The internal and public S3 clients use path-style addressing unless deployment settings
explicitly choose virtual-host style. Presigned signatures must be generated for the
exact host that the browser will use.

## 6. Supported purposes and policies

`purpose` is stored as `VARCHAR(64)` rather than a PostgreSQL enum so new purposes do
not require a database migration. The application maintains a strict registry.

| Purpose | Actor | Binding | Maximum size |
|---|---|---|---:|
| `user_avatar` | owner or `ADMIN` | `user/{JWT sub}` | 5 MiB |
| `product_image` | `ADMIN` | `product/{uuid}` | 15 MiB |
| `brand_logo` | `ADMIN` | `brand/{uuid}` | 10 MiB |
| `review_image` | authenticated owner | optional `review/{uuid}` | 10 MiB |
| `drop_image` | `ADMIN` | `drop/{uuid}` | 15 MiB |
| `notification_attachment` | `ADMIN` | `notification/{uuid}` | 10 MiB |
| `public_asset` | `ADMIN` | optional safe entity type/UUID | 25 MiB |

The initial safe content-type registry contains JPEG, PNG, WebP, GIF, and PDF. HTML,
JavaScript, SVG, XML, executable files, archives, unknown formats, and mismatches
between declaration and detected bytes are rejected. Raster images are served inline;
PDFs are served as attachments. Adding a type later requires an explicit validation and
delivery policy.

`entity_type` must match `^[a-z][a-z0-9_]{1,63}$`. Entity identifiers are UUIDs. Media
checks binding shape and actor permission but does not make synchronous calls to domain
services. This avoids coupling availability and mirrors the current URL-based Catalog
integration.

## 7. Data model

The `media_assets` table contains:

- `id UUID`, primary key, generated by the application;
- `uploader_id UUID`, taken exclusively from the verified JWT;
- `purpose VARCHAR(64)`, application-policy key;
- `entity_type VARCHAR(64) NULL`;
- `entity_id UUID NULL`;
- `status VARCHAR(32)`;
- `visibility VARCHAR(16)`, fixed to `public` in v1;
- `bucket VARCHAR(255)`;
- `object_key VARCHAR(1024)`, unique;
- `original_filename VARCHAR(255)`, sanitized display name;
- `declared_content_type VARCHAR(255)`;
- `detected_content_type VARCHAR(255) NULL`;
- `expected_size BIGINT`;
- `actual_size BIGINT NULL`;
- `sha256 CHAR(64) NULL`;
- `width INTEGER NULL`;
- `height INTEGER NULL`;
- `upload_expires_at TIMESTAMPTZ`;
- `uploaded_at TIMESTAMPTZ NULL`;
- `delete_requested_at TIMESTAMPTZ NULL`;
- `deleted_at TIMESTAMPTZ NULL`;
- `failure_code VARCHAR(64) NULL`;
- `created_at TIMESTAMPTZ`;
- `updated_at TIMESTAMPTZ`.

Constraints include positive expected/actual size, nonblank identifiers, the supported
visibility, and valid timestamps. Indexes cover:

- unique `object_key`;
- `(uploader_id, created_at DESC)`;
- `(entity_type, entity_id, purpose, status)`;
- `(status, upload_expires_at)`;
- `(status, delete_requested_at)`.

No database foreign key points at another service.

### 7.1 State machine

Allowed transitions are:

```text
PENDING -> VERIFYING -> READY
PENDING -> EXPIRED
PENDING -> REJECTED
VERIFYING -> PENDING       temporary S3 failure, retryable
VERIFYING -> REJECTED      permanent validation failure
READY -> DELETING -> DELETED
DELETING -> DELETING       retry after temporary S3 failure
```

Application methods enforce transitions; direct arbitrary status assignment is not part
of the service interface.

### 7.2 Object keys and immutability

Object keys use:

```text
{purpose}/{yyyy}/{mm}/{asset_id}/{sanitized_filename}
```

The filename is reduced to a safe basename, normalized, length-limited, and stripped of
path separators, control characters, NUL, `.`/`..`, and unsafe characters. The asset ID
ensures uniqueness. Existing objects are never overwritten. Replacing an image creates
a new asset and URL; this permits `Cache-Control: public, max-age=31536000, immutable`.

## 8. HTTP API

All errors use the repository's `{ "error": { "code", "message", "request_id" } }`
envelope.

### 8.1 Create upload

`POST /api/v1/media/uploads` requires an access JWT.

Request:

```json
{
  "purpose": "product_image",
  "filename": "front.webp",
  "content_type": "image/webp",
  "size": 483920,
  "entity_type": "product",
  "entity_id": "0198f32e-0000-7000-8000-000000000001"
}
```

Media validates authorization, purpose policy, filename, type, size, pending-session
quota, asset-count quota, and byte quota. It inserts a `PENDING` row, generates an exact
object key, and returns `201` with:

- public asset metadata;
- browser-visible presigned POST URL;
- all required form fields;
- expiry timestamp;
- completion endpoint.

The S3 policy fixes bucket, key, content type, maximum length, and service metadata, and
expires after the configured interval (10 minutes by default). It must not expose the
S3 secret.

### 8.2 Complete upload

`POST /api/v1/media/assets/{asset_id}/complete` requires the owner or `ADMIN`.

The operation:

1. locks and reads the asset;
2. rejects expired, rejected, deleting, or deleted assets;
3. returns the existing result when already `READY`;
4. transitions `PENDING` to `VERIFYING`;
5. calls S3 `HeadObject` and checks bucket, key, byte size, declared type, and service
   metadata;
6. streams the object through a bounded validator;
7. calculates SHA-256;
8. detects the real content type from the bytes;
9. fully verifies raster-image decoding and records dimensions;
10. rejects decompression bombs and configured pixel-limit violations;
11. stores final metadata and transitions to `READY`;
12. returns the stable public URL.

Permanent validation failure removes the object best-effort and records `REJECTED` with
a non-sensitive failure code. Temporary S3 failure restores a retryable state and
returns `503`. Concurrent and repeated completion requests are safe and idempotent.

### 8.3 Read asset

`GET /api/v1/media/assets/{asset_id}` is anonymous for `READY` public assets. Non-ready
assets require the owner or `ADMIN`. Deleted assets return `404`.

### 8.4 Entity assets

`GET /api/v1/media/entities/{entity_type}/{entity_id}/assets` returns paginated `READY`
assets. Optional `purpose`, `limit`, and `offset` filters are supported. It is anonymous
because every v1 asset is public.

### 8.5 Owner history

`GET /api/v1/media/assets/mine` requires JWT and supports status, purpose, limit, and
offset filters. Admin-only listing supports uploader, entity, status, and time filters.

### 8.6 Bind asset

`PATCH /api/v1/media/assets/{asset_id}/binding` attaches an existing owner asset to a
domain entity. This supports uploading review images before the review exists. Binding
must comply with purpose policy. Administrative assets require `ADMIN`; user assets
require their original uploader. Rebinding a ready asset is explicit and audited in
logs.

### 8.7 Delete asset

`DELETE /api/v1/media/assets/{asset_id}` requires the owner or `ADMIN` and returns
`202`. It atomically changes `READY` or `PENDING` to `DELETING`; a worker performs the
physical S3 deletion and then marks it `DELETED`. Repeated deletion is idempotent.
Failures remain retryable without losing the requested action.

### 8.8 Operational endpoints

- `GET /health/live` verifies the process;
- `GET /health/ready` verifies PostgreSQL and the configured existing S3 bucket;
- `GET /metrics` exposes Prometheus metrics.

## 9. Authorization and quotas

Media uses `shared/jwt_verifier` and the repository's local JWT verification pattern.

- Anonymous actors may read ready public metadata and public objects only.
- Users may upload/delete their own `user_avatar` and `review_image` assets.
- `user_avatar` must bind to the JWT subject.
- `product_image`, `brand_logo`, `drop_image`, `notification_attachment`, and
  `public_asset` require `ADMIN`.
- The request can never select `uploader_id` or `object_key`.
- Pending/non-ready metadata is owner/admin only.
- Admin can inspect and delete any asset.

Default quotas are configurable:

- at most 10 active `PENDING`/`VERIFYING` sessions per user;
- at most 200 ready user-managed assets;
- at most 500 MiB total ready user-managed bytes;
- purpose-specific per-object limits from the policy registry;
- admin bypasses user aggregate quota, never the single-file safety limit.

Repository queries and database locking make quota checks deterministic for concurrent
requests. Gateway rate limiting adds coarse abuse protection but does not replace Media
quotas.

## 10. Content security

The implementation must:

- generate keys server-side;
- sign a short-lived exact policy;
- treat extension and client MIME as declarations, not proof;
- validate magic bytes and decode raster images;
- reject dangerous/unknown public formats;
- limit bytes and decoded pixels;
- prevent path traversal and object overwrite;
- avoid logging JWTs, credentials, signatures, form fields, or file bytes;
- translate S3 errors into stable domain errors;
- require TLS for browser-visible S3/public endpoints in production;
- reject default/insecure production credentials;
- disable API docs in production;
- configure trusted hosts and CORS explicitly;
- keep the bucket unlistable anonymously;
- serve raster images inline and PDF with attachment disposition;
- preserve `X-Content-Type-Options: nosniff` at the public S3/proxy layer as an external
  deployment requirement.

Virus scanning is not claimed in v1. The restricted allowlist deliberately excludes
archives and executable formats. Adding arbitrary public file types later requires a
quarantine/scanning design.

## 11. Consistency, cleanup, and failures

A separate `media-cleanup` process uses the same application and storage abstractions.
It polls in bounded batches and uses row locks with `SKIP LOCKED`, allowing multiple
workers safely.

It performs two jobs:

1. expire old `PENDING` sessions, delete any object uploaded without completion, and
   mark the row `EXPIRED`;
2. process `DELETING` assets, delete the S3 object idempotently, and mark `DELETED`.

Retries use bounded exponential backoff with jitter. A missing object is success for
deletion. Rows retain failure information without credentials or provider internals.
Deleted/rejected/expired tombstones have configurable retention and may be purged later.

Failure behavior:

- database unavailable: no session is created;
- S3 unavailable during creation: no usable presign is returned;
- S3 unavailable during completion: operation is retryable;
- client uploads but omits completion: expiration cleanup removes the object;
- client retries completion: current `READY` result is returned;
- client retries deletion: current deletion state is returned;
- cleanup crashes after S3 deletion and before DB update: retry sees missing object and
  completes the DB transition;
- public object availability during the brief `DELETING` interval is accepted for v1.

## 12. Configuration

Representative settings use the `MEDIA_` prefix:

```text
MEDIA_ENVIRONMENT
MEDIA_DEBUG
MEDIA_DOCS_ENABLED
MEDIA_DATABASE_URL
MEDIA_S3_INTERNAL_ENDPOINT
MEDIA_S3_PUBLIC_ENDPOINT
MEDIA_S3_ACCESS_KEY
MEDIA_S3_SECRET_KEY
MEDIA_S3_BUCKET
MEDIA_S3_REGION
MEDIA_S3_ADDRESSING_STYLE
MEDIA_S3_SECURE
MEDIA_PUBLIC_BASE_URL
MEDIA_UPLOAD_TTL_SECONDS
MEDIA_CLEANUP_INTERVAL_SECONDS
MEDIA_CLEANUP_BATCH_SIZE
MEDIA_MAX_PENDING_PER_USER
MEDIA_MAX_USER_ASSETS
MEDIA_MAX_USER_BYTES
MEDIA_MAX_IMAGE_PIXELS
MEDIA_JWT_PUBLIC_KEY_DIR
MEDIA_JWT_ALGORITHM
MEDIA_JWT_ISSUER
MEDIA_JWT_AUDIENCE
MEDIA_TRUSTED_HOSTS
MEDIA_CORS_ORIGINS
MEDIA_LOG_LEVEL
MEDIA_LOG_FILE_PATH
MEDIA_ALLOW_INSECURE_INTERNAL_SERVICES
```

`.env.example` documents local/development values but contains no real credentials.
`.env.deploy.example` documents required production values and secure expectations.
Configuration validation distinguishes the HTTP-only internal network endpoint from
the externally visible endpoint, which must use HTTPS in production.

## 13. Code organization

```text
media/
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/20260801_0001_initial.py
├── src/media_service/
│   ├── api/
│   │   ├── dependencies.py
│   │   ├── error_handlers.py
│   │   └── routes/{assets,health,metrics}.py
│   ├── application/
│   │   ├── contracts.py
│   │   ├── schemas.py
│   │   └── services/{assets,cleanup}.py
│   ├── domain/{entities,exceptions,policies}.py
│   ├── infrastructure/{database,models,repositories,s3_storage}.py
│   ├── cleanup_worker.py
│   ├── config.py
│   ├── main.py
│   └── observability.py
├── tests/
├── .env.example
├── .env.deploy.example
├── alembic.ini
├── docker-compose.yml
├── docker-compose.deploy.yml
├── Dockerfile
├── pyproject.toml
├── README.md
└── uv.lock
```

Application code depends on an `ObjectStorage` protocol. The concrete S3 adapter is
compatible with MinIO, AWS S3, Yandex Object Storage, and other S3 providers. Services
depend on repositories and storage protocols, not SQLAlchemy or an S3 SDK directly.

## 14. Repository integration

The root Compose will extend only `media` API and cleanup services. It will not define
MinIO, a MinIO initializer, an S3 volume, or a bucket-creation job. Media Compose files
declare `shide-observability` as an external network and mount the existing public JWT
key volume in the same way as other services.

The infrastructure database initializer gains the `media` PostgreSQL database because
PostgreSQL is already part of the shared infrastructure contract. Gateway gains:

- `/api/v1/media` path routing;
- a suitable upload-session rate limit;
- optional `media.${GATEWAY_DOMAIN}` service routing.

No frontend files change. No Catalog schema migration is required. No existing MinIO
deployment is mutated by code in this repository.

## 15. Observability

Structured logs include request ID, asset ID, uploader ID, purpose, safe state
transition, S3 operation name, latency, and stable error code. They exclude credentials,
JWTs, presigned fields, query signatures, and content.

Metrics include:

- `media_upload_sessions_total`;
- `media_uploads_completed_total`;
- `media_uploads_rejected_total`;
- `media_upload_bytes_total`;
- `media_s3_operations_total`;
- `media_s3_operation_duration_seconds`;
- `media_pending_assets`;
- `media_deletion_queue_size`;
- `media_cleanup_failures_total`;
- standard HTTP request count, latency, and status metrics.

Readiness checks PostgreSQL and `HeadBucket`/equivalent access to the configured existing
bucket without modifying it.

## 16. Testing strategy

Unit tests cover policy lookup, filename sanitization, object-key construction, public
URL escaping, role/ownership decisions, quotas, state transitions, MIME decisions,
idempotent completion/deletion, and S3 error mapping.

API tests cover:

- successful upload-session creation;
- missing or invalid JWT;
- user attempting administrative purposes;
- avatar binding to another user;
- pending-session and byte quotas;
- successful completion;
- missing S3 object;
- size, metadata, MIME, pixel, and decoding mismatch;
- repeated and concurrent completion;
- anonymous ready reads;
- non-ready ownership protection;
- binding and rebinding rules;
- pagination and filters;
- deletion authorization and idempotency;
- health and error envelope behavior.

Storage-adapter tests use a fake for fast deterministic coverage and verify presigned
conditions, HEAD/GET/delete mapping, endpoint selection, path-style addressing, and
redaction. Optional integration tests require explicit test S3 environment variables;
they must never create or alter the shared production bucket. A dedicated configured
test prefix isolates their objects, and cleanup removes only that resolved prefix.

Quality gates are Ruff, strict mypy, Media pytest, repository gateway tests, Docker
Compose configuration validation, and health smoke tests when external dependencies are
available. Tests that require unavailable external shared infrastructure skip with a
clear reason; unit/API coverage remains runnable locally with fakes and SQLite.

## 17. Implementation sequence

1. Scaffold the Media package and configuration.
2. Define domain policies, states, exceptions, and storage/repository protocols.
3. Add SQLAlchemy persistence and the initial Alembic migration.
4. Implement the S3 adapter with distinct internal and public clients.
5. Implement presigned-session creation and quotas.
6. Implement completion validation, hashing, image inspection, and idempotency.
7. Implement reads, owner/admin lists, and entity binding.
8. Implement eventual deletion and cleanup worker.
9. Add JWT authorization and consistent error handling.
10. Add observability, readiness, and metrics.
11. Add service/deployment Compose files that use only the external network and S3.
12. Integrate the root Compose, database initializer, and gateway routes.
13. Add unit, API, storage-adapter, integration, and gateway tests.
14. Generate/update the lock file and run all quality gates.
15. Review the final diff to confirm no frontend, self-hosted MinIO, or unrelated
    Inventory changes were introduced.

## 18. Acceptance criteria

The feature is complete when:

- an authenticated permitted actor can create a constrained presigned POST;
- a browser can upload directly to the configured external MinIO endpoint;
- Media verifies and publishes a valid object through an immutable public URL;
- unsafe, oversized, malformed, unauthorized, and mismatched uploads are rejected;
- assets can be queried by ID, owner, and entity binding;
- owner/admin deletion is eventual, idempotent, and retried;
- expired uploads and orphan objects are cleaned safely;
- the service reports database/S3 readiness and exports metrics;
- Docker configuration joins `shide-observability` but defines no MinIO resources;
- existing Catalog URL contracts accept the returned URL unchanged;
- unit/API tests pass without requiring live shared infrastructure;
- optional live-S3 tests operate only under an explicitly configured test prefix;
- Ruff, strict mypy, tests, and Compose validation pass;
- frontend files and existing Inventory worktree changes remain untouched.
