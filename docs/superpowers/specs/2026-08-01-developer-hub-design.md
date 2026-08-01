# FlashMarket Developer Hub Design

**Date:** 2026-08-01  
**Status:** Approved for implementation planning

## Purpose

FlashMarket will expose a public developer hub at `/dev` on the same domain as
the storefront. The hub will document the real public API, show the actual
service topology and readiness state, and allow a visitor to execute operations
permitted by their current FlashMarket session.

The hub is also a portfolio surface. It must communicate the engineering
structure of FlashMarket without publishing internal routes, credentials,
container addresses, or fictional operational data.

## Fixed decisions

- The public URL is `https://${GATEWAY_DOMAIN}/dev`.
- No API or documentation subdomain is introduced.
- The browser uses same-origin relative URLs; the frontend does not embed a
  production hostname.
- The hub is part of the existing React/Vite frontend.
- OpenAPI is exported and merged during CI/build, not assembled from production
  services at request time.
- Existing service `/docs`, `/redoc`, and `/openapi.json` endpoints remain
  disabled in production.
- Every endpoint displayed in production comes from a real FastAPI OpenAPI
  document and a public gateway route.
- Admin operations are visible to everyone with an `Admin only` marker, but
  executable only for a signed-in user whose role is `ADMIN`.
- The finished production page contains no mock endpoints, mock service status,
  fake tokens, simulated responses, or fake business identifiers.

## Existing visual foundation

The uncommitted `frontend/src/components/DevHub` implementation is the visual
starting point. Its editorial dark layout, lime FlashMarket accent, service
grid, API explorer, architecture section, and responsive column structure may
be retained or refined.

The current `mockApiData.js`, mock role switch, simulated request execution,
hard-coded domain, fake operational status, and fictional architecture claims
are development scaffolding only and must not remain in the production bundle.

## Architecture

The existing frontend serves both the storefront and the developer hub:

```text
Browser
  |
  +-- / ----------------------> React storefront
  |
  +-- /dev -------------------> React Developer Hub
  |      |
  |      +-- /dev/openapi.json     generated public contract
  |      +-- /dev/services.json    generated service metadata
  |      +-- /dev/status/<service> sanitized readiness proxy
  |      +-- /api/* and /auth/*    real API execution through gateway
  |
  +-- Nginx gateway ----------> FastAPI services on the Docker network
```

`window.location.origin` is the displayed origin. Requests use relative paths,
so local development, preview deployments, and production all use the domain
that served the page.

## Contract generation

### Discovery

A repository-level generator under `tools/openapi/` discovers API services by
convention:

- a top-level service directory contains `pyproject.toml`;
- its project is a FlashMarket service;
- its application package lives under `src/`;
- it exposes a FastAPI application or application factory from `main.py`;
- the service has at least one public route mapped by `gateway/nginx.conf`.

Workers and support packages that do not meet the API-service convention are
ignored. Discovery order is stable to keep generated output deterministic.

Each service is exported in its own dependency environment through `uv`, so the
generator does not require all service dependencies to coexist in one Python
environment. Calling `app.openapi()` must not start lifespan resources, connect
to PostgreSQL, Redis or RabbitMQ, or require a running service container.

### Public-route selection

The gateway remains the authority for external reachability. The generator
extracts the path prefixes routed to each service from `gateway/nginx.conf` and
keeps only matching OpenAPI operations.

The merged document excludes:

- `/internal/*`;
- `/metrics` and monitoring endpoints;
- per-service health probes;
- `/docs`, `/redoc`, and `/openapi.json`;
- any operation not reachable through the main-domain gateway.

Subdomain routing does not change the public server URL in the merged document.
The merged document declares `/` as its server so interactive requests stay on
the current origin.

### Merge rules

The generator produces OpenAPI 3.1 JSON with FlashMarket-level `info`, a stable
service/tag order, and one shared bearer security scheme.

For every source document it:

1. copies public operations;
2. associates each operation with its owning service;
3. namespaces conflicting component names by service;
4. rewrites all affected local `$ref` values;
5. preserves request bodies, parameters, examples, responses, security, and
   useful vendor extensions;
6. rejects duplicate method/path pairs, unresolved references, invalid schemas,
   and ambiguous ownership.

The generated artifacts are:

- `frontend/public/dev/openapi.json` — the merged API contract;
- `frontend/public/dev/services.json` — service names, route prefixes, operation
  counts, tags, and readiness keys derived from the same generation pass.

These files are build artifacts and are never hand-edited. A failed generation
must fail the build; stale or mock artifacts are not used as fallback.

## Access metadata

OpenAPI security describes authentication but not application roles. The
exporter therefore writes a small FlashMarket extension on every operation:

```python
openapi_extra={"x-flashmarket-access": "admin"}
```

Supported values are:

- `anonymous` — runnable without a session;
- `authenticated` — runnable by any authenticated user;
- `admin` — runnable only when the current profile role is `ADMIN`.

The exporter infers the value from the project's standard FastAPI dependencies:
`require_admin`, `get_current_principal`, and optional/no principal. A route may
set `openapi_extra` explicitly when its access policy cannot be represented by
those shared dependencies. This avoids a separate frontend permission list and
keeps new conventional routes automatic. The generator rejects an operation
whose access cannot be classified safely, and rejects an `/admin` path that
does not use the admin dependency.

The extension controls the developer-hub affordance only. FastAPI dependencies
and business authorization remain authoritative and must reject unauthorized
requests independently of the UI.

## Frontend data flow

On `/dev`, the frontend loads the generated OpenAPI and service metadata in
parallel. It derives all endpoint navigation, filters, method badges, parameter
forms, request bodies, response schemas, service counts, and headline totals
from those documents.

No endpoint catalogue is maintained in JSX. Adding or modifying a FastAPI route
updates the hub after the next successful generation and deployment, provided
the route is exposed by the gateway and has valid access metadata.

The existing `AuthProvider` is reused. It supplies the current user and reacts
to login, logout, refresh, and session expiry. The hub has no independent login
state and no production role switch.

The UI states are:

- guest: anonymous operations are executable; authenticated and admin
  operations remain visible but disabled with an explanation;
- customer: anonymous and authenticated operations are executable; admin
  operations remain visible but disabled and marked `Admin only`;
- admin: every operation allowed by the backend is executable.

## Real request playground

The playground constructs a request from the selected OpenAPI operation. It
supports path parameters, query parameters, declared headers, JSON request
bodies, and operations without a body.

Requests target the current origin and use the existing session behavior:

- the current `fm_access_token` is injected as a bearer token for protected
  operations;
- cookies are sent with `credentials: include`;
- the existing CSRF token mechanism is used where applicable;
- the established refresh flow handles an expired access token;
- logout or failed refresh immediately returns the hub to guest state.

Authorization is a protected header. The raw token is never rendered in the
header editor, response panel, generated examples, logs, clipboard content, or
downloaded output.

Before executing destructive `DELETE` operations or explicitly administrative
mutations, the hub shows a confirmation containing the real method and resolved
path. This confirmation is a UX safeguard, not an authorization control.

The response panel displays the real HTTP status, elapsed time, safe response
headers, and parsed JSON or text. Large bodies are truncated in the rendered
panel with an explicit download action for the complete response.

## Service readiness

The page must not guess that a service is operational. The gateway exposes a
fixed same-origin readiness route for each documented service under
`/dev/status/<service>`. Each route proxies only that service's readiness probe
and reveals no internal hostname, database URL, package version, stack trace, or
credentials.

The frontend requests these routes with a short timeout and maps results to:

- `Operational` for a successful readiness response;
- `Unavailable` for an unsuccessful response;
- `Unknown` when the probe times out or cannot be interpreted.

The headline system status is calculated from these real states. Unknown and
unavailable services are never displayed as operational.

## Page composition

The finished page retains the strong parts of the supplied mockup:

- a dedicated Developer Hub header with a return-to-store action and current
  user state;
- a hero summarizing the generated contract;
- a service overview driven by generated metadata and real readiness;
- a responsive API explorer with endpoint navigation, contract detail, and a
  real request playground;
- a factual architecture overview;
- workflow recipes that link existing operations without simulating execution;
- a concise factual technology and repository footer.

Workflow recipes may describe browsing a drop, managing a wishlist, and
creating an order, but their steps must resolve to operations in the generated
schema. They contain no fake IDs, fake responses, timers, or success animation.
Selecting a step navigates to the corresponding real operation in the explorer.

Any statement about routing, authentication, protocols, isolation, storage, or
messaging must match the repository. In particular, the page must not claim that
Nginx validates JWTs, that the project uses internal gRPC channels, or that each
service has a separate Docker network when those statements are false.

## Loading and failure behavior

- OpenAPI and service metadata display skeletons while loading.
- Missing, malformed, or incompatible generated data produces an explicit
  `API reference unavailable` state.
- The UI never replaces missing contract data with mock endpoints.
- A failed readiness request produces `Unavailable` or `Unknown`, not a fake
  green status.
- API error responses display their real status and a safe response body.
- Non-JSON responses are treated as text.
- Invalid user input is rejected before request execution with a field-level
  explanation.
- An endpoint removed between builds cannot be silently retained from cached
  JavaScript data.

## CI and deployment

The gateway/frontend workflow runs contract generation before the frontend
image build. Its path triggers include API source, API dependency manifests and
locks, gateway routing, generator code, Dev Hub code, and workflow changes.

The pipeline performs:

1. service discovery and isolated schema export;
2. public-route filtering and schema merge;
3. OpenAPI validation and contract checks;
4. frontend tests and production build;
5. frontend/gateway deployment;
6. smoke checks for `/dev`, `/dev/openapi.json`, and readiness routes.

A route change cannot deploy an updated developer hub unless the real contract
is generated successfully. Production retains no runtime dependency on service
OpenAPI endpoints.

## Verification

### Generator tests

- deterministic service discovery;
- exclusion of workers and non-API packages;
- extraction of gateway service/path ownership;
- filtering of internal and operational routes;
- duplicate method/path rejection;
- component namespacing and recursive `$ref` rewriting;
- unresolved reference rejection;
- required access metadata;
- stable generated output.

### Frontend tests

- guest, customer, and admin execution rules;
- admin routes remain visible to non-admin visitors;
- current-origin request construction;
- path, query, header, and JSON-body serialization;
- real JSON and text response rendering;
- session expiry and role change updates;
- destructive-operation confirmation;
- authorization-token redaction;
- unavailable contract and unavailable service states;
- keyboard access and responsive explorer state transitions.

### Contract and smoke tests

- every merged operation is routed by the main-domain gateway;
- no internal or monitoring path is present;
- `/dev` serves the Developer Hub after a production build;
- `/dev/openapi.json` is valid OpenAPI 3.1;
- readiness routes return only the approved public status contract;
- the production source graph does not import `mockApiData.js`;
- the production bundle contains no `Mock Runtime`, fake bearer token, mock
  response simulator, or hard-coded documentation domain.

## Out of scope

- a separate docs or API domain;
- a new API gateway product or a custom reverse-proxy service;
- runtime merging of production OpenAPI documents;
- exposing internal endpoints;
- replacing backend authorization with frontend role checks;
- a sandbox database or automatic seed reset;
- automatic execution of multi-step business flows;
- changing unrelated storefront behavior.

## Completion criteria

The feature is complete when a successful production deployment serves a
responsive `/dev` page on `GATEWAY_DOMAIN`, all displayed API and status data is
derived from the current repository and running services, current FlashMarket
sessions govern real request execution, admin operations follow the agreed
visibility rules, and no mock data or simulator remains in the production page.
