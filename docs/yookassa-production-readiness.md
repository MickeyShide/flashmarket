# YooKassa production-readiness tracker

Updated: 2026-08-25

This is the living implementation tracker for the test-only, production-grade YooKassa architecture described in [the approved design](superpowers/specs/2026-08-25-yookassa-production-hardening-design.md).

Receipt delivery and provider-switch remediation are tracked against the
[approved follow-up design](superpowers/specs/2026-08-25-yookassa-receipt-and-provider-isolation-design.md)
and its [implementation plan](superpowers/plans/2026-08-25-yookassa-receipt-and-provider-isolation-implementation.md).

Status markers:

- `[ ]` planned;
- `[~]` in progress;
- `[x]` implemented and verified;
- `[!]` externally blocked with a documented reason.

Live payments must remain disabled. An item is marked complete only after its relevant automated checks pass.

## 1. Baseline and CI

- [x] Smart Payment redirect, verified webhook state, full test refund, and return page baseline.
- [x] Pydantic parses `PAYMENTS_YOOKASSA_TEST_MODE_REQUIRED=true` while rejecting `false`.
- [x] Every public payment route has an explicit OpenAPI access classification.
- [x] Repository OpenAPI artifacts regenerate successfully.
- [x] Approved production-hardening design is committed.
- [x] Production workflow consumes test-shop GitHub configuration with fail-fast validation and never permits live mode.
- [x] Baseline pushed to `origin/main` (`d5f4626`).

## 2. Provider HTTP resilience

- [x] One process-lifetime pooled `httpx.AsyncClient` for API and worker processes.
- [x] Explicit connection/keep-alive pool limits.
- [x] Separate read/write concurrency gates.
- [x] Typed provider error taxonomy for rejection, rate limiting, and uncertain results.
- [x] Increasing backoff with jitter; no zero-delay retry.
- [x] Interactive retry budget separated from durable worker reconciliation retries.
- [x] Circuit breaker that does not turn uncertain writes into definite failures.
- [x] Sanitized provider error IDs and latency/concurrency metrics.

## 3. Durable provider operations

- [x] Additive `provider_operations` migration and repository.
- [x] Immutable canonical request payload and request hash.
- [x] Stable idempotence key bound to the request hash.
- [x] States `NEW`, `IN_FLIGHT`, `UNKNOWN`, `SUCCEEDED`, `FAILED`, `QUARANTINED`.
- [x] Never automatically POST an unknown operation after 24 hours.
- [x] Crash-after-provider-success recovery tests.
- [x] Bounded list-based recovery when no external ID is known.

## 4. Webhook ingestion

- [x] Additive `webhook_inbox` migration and repository.
- [x] Semantic deduplication without relying on a provider event ID.
- [x] Handler persists then returns HTTP 200 without provider network I/O.
- [x] Inbox worker verifies current provider state through GET.
- [x] Duplicate, out-of-order, malformed, and permanent-mismatch handling.
- [x] Retry and quarantine state with bounded attempts.
- [x] Dedicated gateway location, body limit, source allowlist, and independent burst policy.
- [x] Production gateway deploy copies and mounts the versioned YooKassa source allowlist read-only.

## 5. Reconciliation

- [x] Worker claims bounded batches with `FOR UPDATE SKIP LOCKED` for operations, webhooks, attempts, and refunds.
- [x] No database transaction remains open during provider I/O.
- [x] Reconcile unknown create operations.
- [x] Reconcile active/stale payment attempts without trusting local expiry alone.
- [x] Reconcile pending refunds, including canceled refunds without a webhook.
- [x] Backoff, jitter, heartbeat, lag, quarantine metrics, and alert rules.

## 6. Multiple payment attempts

- [x] Additive `payment_attempts` migration and repository.
- [x] At most one active attempt per order-level payment.
- [x] Concurrent checkout calls converge on one attempt and operation.
- [x] Expired/canceled attempt creates a new attempt and idempotence key.
- [x] Existing payment API remains compatible through the aggregate/read model.
- [x] HTTP 202 preparation response exposes stable attempt state and retry hint.

## 7. Normalized refunds

- [x] Additive `refunds` migration and repository.
- [x] Full and partial refund accounting.
- [x] Persisted refund balance ownership independent of workflow status.
- [x] Concurrent refundable-balance protection through aggregate row locking.
- [x] Multiple refunds cannot exceed the captured amount.
- [x] `rejected_by_timeout` creates a new operation/key with backoff.
- [x] `insufficient_funds`, `rejected_by_payee`, and `general_decline` stop blind retries.
- [x] Compatibility fields remain synchronized during migration.

## 8. Frontend flow

- [x] Checkout handles immediate redirect and HTTP 202 preparation.
- [x] Preparation and return polling use increasing delay plus jitter.
- [x] Polling pauses in hidden tabs and remains bounded.
- [x] Expired/canceled attempts offer a new attempt without a new order.
- [x] Frontend tests and production build pass.

## 9. Ledger, receipts, and reports

- [x] Append-only `financial_ledger` migration and idempotent posting.
- [x] Successful payment and refund transitions create ledger entries atomically.
- [x] Receipt contracts use immutable order-line snapshots and exact totals.
- [x] Validate item limits, VAT code, subject, mode, measure, and customer contact.
- [x] Persist `NEEDS_CONTACT` or simulated test-mode receipt state without enabling fiscal writes.
- [x] Daily report import model, content-hash idempotency, and Moscow business date.
- [x] Deterministic report fixtures and discrepancy quarantine without mutating payment state.
- [!] Actual production fiscal register connection requires merchant/legal setup.
- [!] Actual YooKassa daily report retrieval requires a production merchant account.

## 10. Observability and final verification

- [x] Provider latency/outcome, concurrency, and circuit metrics.
- [x] Unknown-operation age/count metrics and alerts.
- [x] Webhook inbox depth, lag, retries, and quarantine metrics.
- [x] Attempt/refund/reconciliation age and drift metrics.
- [x] No high-cardinality financial identifiers in metric labels.
- [x] Migration upgrade verification from an empty database through revision `20260825_0014`.
- [x] Payments unit/integration/concurrency suite.
- [x] Ruff for changed code and strict mypy.
- [x] Repository OpenAPI generation and tests.
- [x] Frontend tests and production build.
- [x] Final security and failure-mode audit completed; both high-severity fail-safe accounting defects are resolved in `9b335a7` and re-verified in `docs/yookassa-security-review-2026-08-25.md`.
- [x] Implementation, audit, and approved security fixes are committed and pushed to `origin/main`.

## 11. Test-shop receipt rejection and provider isolation

Production test evidence on 2026-08-25 reopened receipt delivery and provider
isolation work. YooKassa rejected payment creation with `invalid_request`,
`parameter=receipt`, and `description=Receipt is missing or illegal`. A separate
worker request sent a historical `mock-*` ID to YooKassa after the provider switch.

- [x] Capture the exact YooKassa request and error response from the event log.
- [x] Identify the missing provider receipt serialization root cause.
- [x] Identify unscoped reconciliation claims as the `mock-*` request root cause.
- [x] Approve and commit the remediation design.
- [x] Write the implementation plan.
- [~] Implement provider-neutral receipt contracts and YooKassa serialization.
- [ ] Propagate authenticated profile email into new order receipt snapshots.
- [ ] Enrich and freeze legacy `NEEDS_CONTACT` snapshots at checkout.
- [ ] Add payment and refund receipt payloads with exact-total validation.
- [ ] Scope all financial worker claims and reconciliation by provider.
- [ ] Log bounded, sanitized YooKassa error details without public disclosure.
- [ ] Add receipt, retry, concurrency, refund, and provider-switch regressions.
- [ ] Apply the receipt-state migration and regenerate OpenAPI artifacts.
- [ ] Pass all affected service, frontend, deployment, migration, lint, and type checks.
- [ ] Commit and push the implementation in reviewable units.
- [ ] Verify a new test-shop payment reaches the hosted confirmation page.
- [ ] Verify YooKassa receives no further `mock-*` identifiers.

## Verification log

| Date | Stage | Checks | Result |
|---|---|---|---|
| 2026-08-25 | CI repair | Payments `25 passed`; strict mypy; changed-file Ruff/format; OpenAPI generation; OpenAPI tests `4 passed` | Pass |
| 2026-08-25 | Provider resilience | Payments `29 passed`; strict mypy; scoped Ruff/format | Pass |
| 2026-08-25 | Durable provider operations | Payments `31 passed`; strict mypy; scoped Ruff/format | Pass |
| 2026-08-25 | Durable webhook inbox | Payments `33 passed`; strict mypy; scoped Ruff/format; gateway syntax not runnable because local Docker daemon is unavailable | Pass with noted local-tool limitation |
| 2026-08-25 | Multiple payment attempts | Payments `36 passed`; strict mypy; scoped Ruff/format; concurrent file-backed SQLite test | Pass |
| 2026-08-25 | Normalized refunds | Payments `42 passed`; strict mypy; scoped Ruff/format; partial/over-refund, reason-policy, and unknown-result recovery tests | Pass |
| 2026-08-25 | Frontend payment flow | Frontend `25 passed`; Vite production build; Payments `42 passed`; strict mypy; scoped Ruff/format | Pass |
| 2026-08-25 | Ledger, receipts, and reports | Payments `47 passed`; full Payments Ruff; strict mypy; deterministic Moscow-time CSV reconciliation | Pass |
| 2026-08-25 | Attempt reconciliation and observability | Payments `48 passed`; full Payments Ruff; strict mypy; Alembic empty SQLite upgrade through `20260825_0013`; Prometheus alert rules added | Pass |
| 2026-08-25 | Final verification before security fixes | OpenAPI generation; OpenAPI/gateway contracts `16 passed`; frontend `25 passed` and production build; dependency audits found 0 known vulnerabilities; secrets scan found 0 exposed credentials | Pass with two security-review fixes pending |
| 2026-08-25 | Approved security fixes | Payments `52 passed`; full Ruff/format; strict mypy; empty migration upgrade and seeded reservation backfill through `20260825_0014`; OpenAPI/gateway `16 passed`; frontend `25 passed` and production build | Pass |
| 2026-08-25 | Test-shop deployment wiring | Payments deployment and gateway/OpenAPI contracts `20 passed`; workflow YAML parsed; production Compose rendered; official webhook IP list re-verified; GitHub Payments, Gateway, and Reliability runs succeeded; main-domain Payments readiness and return page returned `200`, foreign-source webhook request returned `403` | Pass |
