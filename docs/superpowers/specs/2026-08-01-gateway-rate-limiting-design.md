# Gateway Rate Limiting Design

## Goal

Add IP-based request limiting at the Nginx API Gateway so abusive clients and
traffic spikes cannot overwhelm FlashMarket services. Limits must reflect the
risk and expected traffic of each route group, apply consistently through the
main domain and service subdomains, and preserve normal flash-sale bursts.

## Scope

This change covers public API traffic entering the existing Nginx gateway. It
does not add application-level quotas, user- or token-based limits, Redis, a
new gateway implementation, or coordination between multiple gateway
instances. The frontend's static assets and the gateway's health and
monitoring endpoints remain outside rate limiting.

The current deployment runs one gateway instance, so Nginx shared-memory
counters provide the required consistency without another runtime dependency.

## Architecture

Nginx owns four shared-memory request-limit zones. Every zone uses the same
normalized client key derived from `$binary_remote_addr`. The existing
trusted-proxy `real_ip` directives are moved from the main server block to the
HTTP context without changing their trusted networks or header semantics, so
the same normalization applies to the main domain and every service
subdomain. Because a zone is shared by every location that references it,
requests through the main domain and the corresponding service subdomain
consume the same per-IP quota.

The profiles are:

| Profile | Routes | Sustained rate | Burst |
| --- | --- | ---: | ---: |
| `auth` | Auth, users, sessions, and admin identity APIs | 5 requests/second | 10 |
| `transaction` | Orders, payments, promocodes, and wishlist APIs | 10 requests/second | 20 |
| `catalog` | Products, categories, brands, drops, and drop administration | 50 requests/second | 100 |
| `general` | Inventory, notifications, and other explicitly routed APIs | 20 requests/second | 40 |

Each zone reserves 10 MiB. All profiles use `nodelay`: traffic within the
sustained rate and configured burst proceeds immediately, while traffic beyond
the burst is rejected rather than queued inside the gateway.

## Route Classification

On the main domain, each existing API `location` receives exactly one profile.
The legacy unversioned Auth routes receive the `auth` profile as well. The
frontend catch-all `location /` has no limiter, because a browser may fetch
many static assets in parallel and those requests do not reach an API service.

Service subdomains use the profile matching their service:

- `auth.*` uses `auth`;
- `catalog.*` and `drops.*` use `catalog`;
- `orders.*`, `payments.*`, and `wishlist.*` use `transaction`;
- `inventory.*` and `notifications.*` use `general`.

The client-key mapping returns an empty key for `/health`, paths below
`/health/`, `/metrics`, `/prometheus`, paths below `/prometheus/`, and
`/nginx_status`. Nginx does not account requests with an empty limit key. This
keeps readiness checks and metrics collection reliable on both the main domain
and service subdomains while leaving all other subdomain paths protected.

Any future API route must select one of the four profiles. Tests enforce this
for every API location present in the gateway configuration so a new route
cannot silently bypass the limiter.

## Request and Error Flow

For an API request:

1. Existing `real_ip` directives determine the effective remote address.
2. The exemption map returns either an empty key for a service endpoint or the
   binary client address.
3. The route's profile checks that key in its shared-memory zone.
4. An allowed request is proxied exactly as it is today.
5. A request beyond the profile's burst is handled locally by Nginx and never
   reaches the upstream service.

Rejected requests return HTTP `429 Too Many Requests` with
`Content-Type: application/json`, `Retry-After: 1`, and this body:

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Too many requests"
  }
}
```

An internal named error handler owns this response. Upstream-generated 429
responses are not intercepted, so an application remains free to return a
more specific rate-limit error. Gateway rejections are logged by Nginx at
`warn` level. Logs contain the normal request metadata but no new credentials,
tokens, or request bodies.

## Configuration Structure

The trusted-proxy `real_ip` directives, shared key mapping, and
`limit_req_zone` declarations live in the HTTP context at the beginning of
`gateway/nginx.conf`, before the server blocks. Common response status and
logging behavior is configured on each public server. Individual API
locations contain the selected `limit_req` directive, making route
classification visible beside the upstream target.

Rates and burst sizes are initially explicit configuration constants rather
than environment variables. This keeps the Nginx template and deployment
contract small. Changing a limit requires a reviewed gateway configuration
change and restart, which is acceptable for the current deployment model.

## Components

- `gateway/nginx.conf`: exemption key map, four zones, per-route profile
  assignment, 429 handler, response status, and warning-level logging.
- `gateway/README.md`: profile table, exemption list, single-instance scope,
  and instructions for tuning limits.
- `tests/test_gateway_routing.py`: static configuration-contract tests for
  zones, route coverage, exemptions, and the 429 contract.

No backend or frontend source file changes, and no new package or service is
required.

## Testing and Verification

Automated tests cover:

- all four zones, their rates, and the shared 10 MiB allocation;
- the exact burst and `nodelay` setting for each profile;
- the profile assigned to every main-domain API route;
- the profile assigned to every service subdomain;
- the absence of rate limiting from the frontend catch-all;
- empty-key exemptions for health and monitoring paths;
- HTTP 429, JSON content type, `Retry-After: 1`, and the stable error body;
- preservation of every existing dynamic upstream and path-routing rule.

Verification also renders the template with the current gateway environment
and runs `nginx -t` using the existing `nginx:alpine` Compose service. The root
gateway test suite then runs to detect both new limiter regressions and changes
to existing routing.

## Acceptance Criteria

- Every public API route on the main domain and every service subdomain is
  protected by the agreed profile.
- The existing trusted proxy allowlist and header behavior are unchanged, but
  client-IP normalization applies consistently to every public server block.
- Main-domain and subdomain access share a quota for the same IP and profile.
- Requests within the rate and burst are proxied without artificial delay.
- Excess requests receive the documented 429 response without reaching an
  upstream service.
- Frontend assets, health probes, Prometheus, metrics, and `nginx_status` are
  not counted.
- The rendered Nginx configuration passes `nginx -t`.
- Existing and new gateway tests pass.

## Operational Constraint

Counters are local to one Nginx gateway process group. If FlashMarket later
runs multiple gateway replicas, each replica will enforce its own quota and
the effective aggregate limit will scale with the replica count. A distributed
limiter or ingress-native shared policy must be designed before that migration;
it is intentionally outside this change.

## Out of Scope

- Distributed counters backed by Redis or another datastore;
- per-user, per-session, API-key, tenant, or global quotas;
- dynamic administration or runtime editing of rates;
- rate-limit response headers that expose remaining quota;
- application-level changes to Auth's existing Redis limiter;
- Web Application Firewall rules, bot detection, or CAPTCHA;
- rate limiting frontend static assets or internal monitoring traffic.
