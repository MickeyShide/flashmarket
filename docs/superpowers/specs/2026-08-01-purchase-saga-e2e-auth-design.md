# Purchase Saga E2E Authentication Design

## Goal

Restore the Purchase Saga end-to-end workflow after local JWT authorization became mandatory. The test stack must start with a valid Auth signing key, fail clearly when a required service is unavailable, and exercise the saga with identities issued by Auth.

## Root cause

The root Compose file extends the Auth API but removes its dependency on the Auth key generator. On a clean CI runner, the root project therefore creates empty key volumes and starts every JWT-consuming API without a public key. Fail-fast verifier validation terminates those APIs. Gateway health remains independent of upstream health, and the workflow's readiness loop does not return a failure after its deadline, so pytest receives an Nginx `502 Bad Gateway` instead of a setup error.

The saga tests also predate route authorization. Their HTTP client has no access token, their user ID is an arbitrary UUID rather than an Auth user, and the same client performs both administrator-only setup and customer-owned operations.

## Stack startup

The root Compose project will expose an `auth-keygen` service by extending Auth's existing key generator. The Auth API will depend on successful completion of that service. All Auth and downstream containers will continue to use the root project's separated private and public named volumes; only Auth receives the private volume.

The CI workflow will stop creating unrelated global JWT volumes. Docker Compose owns the root project's temporary volumes and removes them during teardown.

The readiness loop will track all required APIs and fail the setup step when any service remains unhealthy at the deadline. The existing always-run diagnostic step will then report container status, logs, network membership, and direct health checks. Pytest will not run after a failed setup step.

## Test identities and authorization

CI will create an ephemeral administrator with Auth's supported `create-admin` CLI after the stack is healthy. Test credentials are fixed, non-production values scoped to the disposable CI environment and supplied to pytest through environment variables.

Session-scoped test setup will log the administrator in through the public Gateway and create an administrator HTTP client. Each saga test will register a distinct customer through Auth and use the returned user ID and access token for a customer HTTP client.

Administrator requests will create categories, products, and initial stock. Customer requests will reserve stock, create and inspect orders, inspect and transition payments, read notifications, and verify owner-visible stock state. This preserves both saga coverage and the route authorization contract.

## Failure handling

Authentication setup must assert response status and include response bodies in failures. A failed admin login or customer registration aborts the test before business operations. Service startup failures abort the workflow before pytest and retain the existing diagnostic output.

The `integration` pytest marker will be registered at the repository root so CI output contains no unknown-marker warning.

## Verification

Verification consists of:

1. rendered Compose checks proving `auth-keygen` exists, Auth depends on it, and downstream services mount only the public key volume;
2. a clean-volume stack startup with every critical service healthy;
3. both Purchase Saga E2E scenarios using real Auth-issued tokens;
4. service-level JWT verifier, Auth, Catalog, Inventory, Orders, Payments, Notifications, Wishlist, and Drops regression suites;
5. workflow YAML and Git diff validation.

## Acceptance criteria

- A clean CI runner generates an Auth key pair before protected APIs start.
- The private signing key is mounted only into Auth key generation and Auth API containers.
- A readiness timeout fails the setup step rather than allowing pytest to receive gateway 502 responses.
- Admin-only setup uses an Auth-issued ADMIN token.
- Owner-scoped saga operations use an Auth-issued CUSTOMER token whose `sub` matches request ownership.
- Both success and payment-failure sagas pass.
- The integration marker warning is removed.
