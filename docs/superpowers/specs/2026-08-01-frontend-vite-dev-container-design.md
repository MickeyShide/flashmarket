# Frontend Vite Dev Container Design

## Goal

Make the default local `make up` workflow run the FlashMarket frontend as a
Vite development server inside Docker. Editing frontend files on the host must
update the browser automatically through Vite hot module replacement without
rebuilding or restarting the container.

Production image behaviour must remain unchanged: production continues to use
the compiled static bundle served by nginx.

## Selected Approach

The frontend Dockerfile will contain a dedicated `dev` stage based on Node 20.
The local frontend Compose service will build that stage and run
`npm run dev -- --host 0.0.0.0`. The existing build and final nginx stages will
remain the default production image path.

This keeps local and production runtimes explicit while allowing the existing
root Compose project and `make up` command to remain the only local entrypoint.

## Local Container Layout

The local frontend service will:

- publish Vite on `127.0.0.1:${FRONTEND_PORT:-3000}`;
- bind-mount the `frontend` directory to `/app` so host edits are visible
  immediately;
- mount a dedicated named volume at `/app/node_modules` so host dependencies do
  not replace the Linux dependencies installed in the image;
- enable file polling for reliable change detection through Docker Desktop on
  Windows;
- join the existing external `shide-observability` network like the rest of the
  local stack;
- keep the existing restart policy and participate in Compose readiness.

The named dependency volume is persistent and is not removed by normal
`make down`.

## Vite Networking and HMR

Vite will listen on `0.0.0.0:3000`. Its browser-facing port remains 3000, so the
HMR client can reconnect through `localhost:3000` without a separate host or
port override.

The existing proxy prefixes `/api`, `/auth`, `/users`, and `/sessions` will use
an environment-controlled upstream. Local Docker Compose sets the upstream to
`http://gateway`, which resolves through Docker DNS. A direct host invocation
of `npm run dev` keeps a localhost fallback for developer convenience.

Polling will be enabled only when requested by the container environment, so a
direct host invocation can continue to use native filesystem events.

## Production Isolation

The final Dockerfile stage will continue to:

1. install dependencies reproducibly with `npm ci`;
2. build the frontend with `npm run build`;
3. copy `dist` into the nginx image;
4. use the existing production nginx configuration.

`docker-compose.prod.yml` continues to consume a production frontend image and
will not mount source files, run Vite, or expose HMR.

## Failure Behaviour

If dependency installation or Vite startup fails, the frontend container exits
or fails its readiness check, causing `make up` to return a non-zero status and
show Compose service state. The workflow does not silently fall back to a stale
static build.

The Vite API proxy must fail visibly when the gateway is unavailable; it must
not reroute requests to an unrelated host service.

## Verification

Implementation verification will cover:

- successful frontend Docker build for both the `dev` target and final nginx
  target;
- valid root and frontend Compose configuration;
- successful `make up` readiness with Vite serving `http://localhost:3000`;
- successful API proxying from Vite to the Docker `gateway` service;
- a host-side frontend source edit becoming visible to the running container
  without image rebuild or container restart;
- successful HMR websocket negotiation;
- unchanged production Compose resolution and production frontend build;
- existing frontend tests.

