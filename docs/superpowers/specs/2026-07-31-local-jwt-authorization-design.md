# Local JWT Authorization Design

## Goal

Add authorization to Catalog, Inventory, Orders, Payments, Notifications, Wishlist, and Drops while keeping Auth as the only service capable of issuing valid access tokens.

Every protected service validates access JWTs locally. It never calls Auth or Redis during request authorization and never receives an Ed25519 private key. Logout, password changes, session revocation, and user blocking therefore take effect in downstream services when the current access token expires.

## Key distribution

Split the current Auth key storage into two Docker named volumes mounted below the existing key directory:

- a private-key volume mounted only into Auth key generation and Auth API processes;
- a public-key volume mounted read-only into Auth API and every protected service.

The key generator continues to create `private/<kid>.pem` and `public/<kid>.pem`, but the directories reside on different volumes. A downstream service receives only the public directory, so it cannot produce a JWT whose signature is accepted by any service.

Each service receives consistent configuration for:

- public-key directory;
- allowed algorithm, fixed to the configured EdDSA algorithm;
- issuer;
- audience.

Public keys are selected by the JWT `kid`. The verifier caches loaded keys and reloads the public directory once when an unknown `kid` is encountered. Rotation must publish the new public key before Auth starts signing with the corresponding private key. Old public keys remain available until every token signed with them has expired.

## Verification-only component

Create one repository-local Python package at `shared/jwt_verifier`, installed as a path dependency by all seven services. Its runtime dependencies are PyJWT and `cryptography`; it remains independent of service models and databases. Each service owns a thin FastAPI adapter under its existing API package for reading the Bearer header and mapping verifier failures to HTTP responses. Dockerfiles copy the shared package before dependency installation, and all seven lockfiles record the same local package version.

The shared package exposes no encode/signing API and loads only public Ed25519 keys. This avoids seven security-sensitive decoder implementations while keeping route-specific authorization inside each owning service.

Successful verification requires:

- an `Authorization: Bearer <token>` header;
- header `typ=JWT`, the configured `alg`, and a known string `kid`;
- a valid Ed25519 signature;
- matching `iss` and `aud`;
- required `sub`, `sid`, `role`, `type`, `jti`, `iat`, and `exp` claims;
- `type=access`;
- valid UUID values for `sub`, `sid`, and `jti`;
- a known role (`CUSTOMER` or `ADMIN`).

The decoded immutable principal contains user ID, session ID, token ID, role, and expiration. FastAPI dependencies provide optional principal, required authenticated principal, and required admin principal.

Authentication failures return `401` with `WWW-Authenticate: Bearer`. An authenticated principal without the required ownership or role receives `403`. Error bodies must not expose token contents, key material, or decoder internals.

Health and metrics endpoints remain independent of JWT validation. A service fails startup when its configured public-key directory is missing, empty, malformed, or incompatible with the configured algorithm.

## Authorization matrix

### Catalog

- Public: read categories, brands, products, and variants.
- Admin: create categories and brands; create, update, and delete products and variants.
- Public product responses retain the existing visibility rules; authorization must not make hidden or archived products newly visible.

### Inventory

- Public: read stock availability.
- Authenticated owner or admin: reserve stock and release a reservation.
- Admin: create/reset stock and commit a reservation through HTTP.
- Reservation operations validate that request `user_id` equals principal `sub`, except for admin.
- RabbitMQ consumers remain machine entrypoints and do not use user JWTs.

### Orders

- Authenticated owner or admin: create an order, read an order, list a user's orders, and execute the current mock confirm/fail transitions.
- Admin: create, list, read, update, and otherwise manage promocodes.
- Authenticated user: validate a promocode for their own `user_id`.
- Request/path `user_id` must equal principal `sub`, except for admin.
- RabbitMQ consumers remain machine entrypoints and do not use user JWTs.

### Payments

- Authenticated owner or admin: create, read, list, confirm, fail, or cancel a payment in the current mock-provider workflow.
- Request/path/body ownership is checked against principal `sub`; admin may operate on another user's payment.
- RabbitMQ consumers remain machine entrypoints and do not use user JWTs.

### Notifications

- Authenticated owner or admin: read one notification, list notifications, and call the existing `send` transition used by Frontend.
- Admin: create a notification or mark delivery as failed.
- Ownership is derived from the persisted notification for ID-based routes and from the path for user lists.
- RabbitMQ consumers remain machine entrypoints and do not use user JWTs.

### Wishlist

- Authenticated owner or admin: add, remove, list, and check items.
- Path `user_id` must equal principal `sub`, except for admin.

### Drops

- Public: active drops, upcoming drops, and drop detail by slug.
- Admin: every route below `/api/v1/admin/drops`.

### Operational routes

- `/health/*` and `/metrics` remain public at the service boundary for probes and monitoring.
- Gateway exposure and infrastructure network policy remain separate defense layers; authorization is enforced in each application even when it is called directly.

## Removal of unused internal HTTP routes

Remove Catalog `GET /api/v1/internal/products/{product_id}` and Inventory `POST /internal/expire` from:

- FastAPI router registration and route modules;
- Gateway proxy locations and Gateway documentation;
- route-level tests;
- service and project documentation;
- `AUTOTEST_PLAN.md` route registry and affected scenarios.

Remove Catalog application/repository code that becomes unreachable only when reference search proves it is not shared with a remaining feature.

Keep Inventory `expire_reservations()` application behavior and repository support. Reservation TTL is a required stock-recovery rule even though no runtime scheduler currently invokes it. Creating a direct background expiry worker is explicitly outside this authorization change and remains documented technical debt.

## Frontend and gateway behavior

Frontend already adds the access token to API calls through its shared client. No new token storage mechanism is introduced.

When a downstream API returns `401`, the existing single refresh-and-retry behavior remains responsible for obtaining a new token from Auth. A `403` is not refreshed because the token is valid but lacks ownership or role.

Remove Gateway locations `/api/v1/internal` and `/internal`. Correct the existing `/api/v1/admin` routing conflict so Auth admin routes and Drops admin routes reach their intended upstreams using specific locations.

## Tests

### Verification contract

Run an identical verifier contract suite for every protected service:

- valid CUSTOMER and ADMIN tokens;
- missing header, wrong scheme, malformed JWT;
- wrong signature, algorithm, issuer, audience, or token type;
- missing/invalid required claims;
- expired and not-yet-valid tokens;
- unknown `kid`, reload with a newly published public key, and still-accepted previous key;
- public-key directory missing, empty, malformed, or containing a mismatched key type;
- confirmation that no private key is mounted in downstream containers.

### Route authorization

For each route class, cover anonymous `401`, wrong-role/foreign-owner `403`, permitted owner success, permitted admin success, and unchanged domain errors after authorization succeeds. Public routes must remain usable without a token and must reject no request merely because an optional malformed token was supplied unless they explicitly consume the principal.

Use signed tokens generated by test-only private keys. Production private keys are never read by downstream tests. Existing business assertions remain in place; authorization tests add state checks proving rejected requests have no database or outbox effects.

### Integration and regression

- Run every service suite and the full saga tests with authenticated users created through Auth.
- Verify Gateway routing for Auth admin and Drops admin separately.
- Inspect rendered Compose configuration to prove only Auth mounts the private-key volume.
- Verify Frontend catalog browsing anonymously and authenticated checkout/profile/wishlist flows.
- Verify public health/metrics behavior without Authorization headers.

## Compatibility and rollout

This is intentionally a breaking security change for anonymous callers of protected routes. Frontend is expected to remain compatible because its shared API client already sends Bearer access tokens.

Roll out in this order:

1. create separated key volumes and publish public keys;
2. add verifier configuration and startup checks to downstream services;
3. add principal dependencies and ownership checks;
4. update Gateway routes;
5. remove obsolete internal routes;
6. run service, contract, Gateway, Frontend, and full-stack tests.

Do not enable protected routes until their containers can read at least the active public key. Rollback restores the previous application images but must not merge the public and private volumes or expose private keys to downstream services.

## Acceptance criteria

- Auth remains the only process with access to an Ed25519 private JWT key.
- All seven downstream APIs validate protected requests locally and make no per-request call to Auth or Redis.
- Every public/authenticated/admin route behaves according to the matrix above.
- A CUSTOMER cannot access another user's resources or any admin mutation.
- An ADMIN can perform the explicitly allowed cross-user and management operations.
- Invalid or expired JWTs consistently return `401`; ownership/role violations return `403`.
- Key rotation works through `kid` without distributing a private key or restarting Auth-dependent request paths.
- Both unused internal HTTP endpoints and their Gateway exposure are gone.
- Existing authorized business flows and anonymous public browsing remain green.
