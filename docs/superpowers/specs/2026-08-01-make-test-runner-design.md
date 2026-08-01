# Make Test Runner Design

## Goal

Provide one repository-level GNU Make interface for running every FlashMarket test locally and in automation, including a self-contained Purchase Saga E2E run.

## Commands

- `make test` runs all non-Docker test suites: Auth, Catalog, Inventory, Orders, Payments, Notifications, Wishlist, Drops, the shared JWT verifier, and Gateway routing tests.
- `make test-e2e` provisions an isolated E2E environment, runs both Purchase Saga scenarios, and removes only resources created by that run.
- `make test-all` runs `test` followed by `test-e2e`.
- `make test-service SERVICE=orders` runs one supported service suite and rejects a missing or unknown service name.
- `make help` documents the available targets and prerequisites.

## Fast test execution

Service suites run through each service's own uv project so their lockfiles and development dependencies remain authoritative. The shared verifier uses its own uv project. Root Gateway tests install only their declared transient pytest dependencies.

The first failing suite stops the target and returns a non-zero exit code. Test output remains visible and identifies the suite being executed.

## E2E lifecycle

The Make targets delegate lifecycle work to one cross-platform Python runner rather than embedding long stateful shell recipes in Make. The runner:

1. chooses a unique Compose project name, network, volume, and infrastructure container names;
2. starts PostgreSQL, Redis, and RabbitMQ on that isolated network with the DNS aliases expected by application configuration, without claiming development host ports;
3. creates service databases and required RabbitMQ virtual hosts;
4. renders a temporary E2E Compose override that points both root network entries at the isolated network, removes unnecessary application host ports, and publishes Gateway on a Docker-assigned loopback port;
5. builds and starts the application stack, waits for every critical service, and fails with diagnostics on timeout;
6. creates an ephemeral administrator through the Auth CLI;
7. runs the Purchase Saga suite with Auth-issued ADMIN and CUSTOMER tokens;
8. uses a guaranteed cleanup handler to remove only its project containers, volumes, network, and temporary files.

The runner must not remove or reuse containers and volumes belonging to the developer's normal FlashMarket stack.

## Platform support

The Makefile uses GNU Make as a thin command dispatcher. A Python runner provides the same implementation on Windows and POSIX systems and invokes uv and Docker without shell-specific loops. It discovers Gateway's assigned port and passes it to pytest through `FLASHMARKET_GATEWAY`.

Windows installation instructions will use the package identifier reported by the local `winget` catalog. WSL and Git Bash remain optional alternatives.

## Verification

- Run `make help` and validate target documentation.
- Run a supported and unsupported `test-service` invocation.
- Run `make test` and confirm every non-Docker suite passes.
- Run `make test-e2e` twice to prove isolated startup and cleanup are repeatable.
- Run `make test-all` and confirm it returns success only when both phases pass.
- Confirm no pre-existing Docker resource is changed or deleted.

## Acceptance criteria

- A developer can run every test with `make test-all`.
- E2E setup and teardown are automatic and isolated.
- Failures return a non-zero status and retain useful diagnostics.
- Windows users receive a verified Make installation command.
- Existing service lockfiles and Docker security boundaries remain unchanged.
