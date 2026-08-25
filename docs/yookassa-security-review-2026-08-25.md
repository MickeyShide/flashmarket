# YooKassa security and failure-mode review

Project: FlashMarket  
Scan date: 2026-08-25  
Scope: repository-wide dependency/secrets scan; deep review of Payments, Orders payment events, gateway, and frontend payment flow  
Languages/frameworks: Python/FastAPI/SQLAlchemy, JavaScript/React/Vite, Nginx, Docker/Compose

## Findings summary

| Severity | Count |
|---|---:|
| Critical | 0 |
| High | 2 |
| Medium | 3 |
| Low | 2 |
| Info | 1 |
| **Total** | **8** |

Dependency audit: 0 known vulnerable third-party packages found.  
Secrets scan: 0 exposed production credentials found.

The two high-severity findings are fail-safe accounting defects. They require review before patches are applied under the security-review workflow. Live payments remain disabled and no production YooKassa credentials are configured, so neither issue is currently reachable with real money in this repository's declared configuration.

## Financial business logic

### HIGH — An unresolved payment can be retried as a second provider payment

Confidence: High  
Locations: `payments/src/payments/application/services/payment.py:333`, `:602`, `:610`

After a successful provider POST returns an object that fails local verification, the attempt is marked `FAILED`. After an unknown create passes the 24-hour idempotency window without a unique bounded-list match, it is marked `EXPIRED`. Both states leave the partial unique active-attempt constraint and let the customer create a new provider payment.

The bounded search examines at most 500 recent objects and a not-found result is not proof that the first POST failed. Under high throughput, pagination truncation, delayed provider indexing, or a malformed-but-successful response, the original payment can still exist and later succeed. A second attempt can therefore produce two charges for one order.

Recommended fix: successful-POST verification failures and aged unresolved operations must remain `UNKNOWN`/manual-review and continue to occupy the active-attempt slot. Only a provider-confirmed terminal `canceled` payment may permit a new attempt.

### HIGH — An unresolved refund releases its balance reservation

Confidence: High  
Locations: `payments/src/payments/application/services/payment.py:1394`, `payments/src/payments/infrastructure/repositories/payment.py:306`, `:374`

After 24 hours without a unique provider match, an `UNKNOWN` refund becomes `QUARANTINED`. `RefundRepository.RESERVED_STATUSES` excludes every quarantined refund, so the same captured balance becomes available for a second refund even though the first provider POST may have succeeded.

Recommended fix: persist reservation ownership independently of workflow status (for example, `funds_reserved`). Keep it set for successful, pending, unknown, and ambiguous/manual-review refunds; release it only after a definite provider rejection or cancellation. Provider-response verification failures must also be converted to an uncertain reserved state instead of leaving `PREPARING` work stranded.

## Test-mode isolation

### MEDIUM — The `test: true` guard is reactive, after the financial POST

Confidence: High  
Locations: `payments/src/payments/application/services/payment.py:273`, `:322`; `payments/src/payments/config.py:148`

The configured guard correctly prevents a `test: false` object from changing local state, but YooKassa only returns that flag after `POST /payments`. Accidentally replacing test-shop credentials with live-shop credentials can therefore create one live pending payment before the application rejects its response.

Recommended fix: add a separately configured expected test-shop identifier and require exact equality at startup, keep the response flag check, and make a false/mismatched result permanently block the order rather than allowing a new attempt. This is defense in depth; YooKassa does not expose a documented pre-POST API flag that cryptographically identifies a test shop.

## Reconciliation integrity

### MEDIUM — Daily report reconciliation is one-directional and ignores fees

Confidence: High  
Locations: `payments/src/payments/application/daily_reports.py:97`, `:115`, `:136`

Every report line is checked against the ledger, but ledger entries missing from the report are not detected. Duplicate provider objects inside one report are also accepted, and the official net/commission fields are not reconciled. This can mark an incomplete or duplicated settlement report as `MATCHED`.

Recommended fix: compare both directions for one Moscow business day, quarantine duplicate provider IDs, and persist/reconcile gross, commission, and net settlement amounts when present.

### MEDIUM — The application does not enforce ledger append-only behavior at the database boundary

Confidence: Medium  
Location: `payments/src/payments/infrastructure/models.py:215`

The repository exposes only posting reads, but the database role can still update or delete `financial_ledger` rows. An application bug or compromised service credential could silently rewrite accounting history.

Recommended fix: use a restricted database role and a PostgreSQL trigger or permissions that reject `UPDATE`/`DELETE`; test the restriction in a real PostgreSQL migration job.

## Data handling and operational hygiene

### LOW — Provider webhook bodies and customer receipt contacts have no retention policy

Confidence: High  
Locations: `payments/src/payments/application/services/payment.py:709`, `payments/src/payments/infrastructure/models.py:250`, `:320`

Processed webhook bodies and future receipt contacts remain in the primary database indefinitely. The body is bounded to 32 KiB and not logged, which limits immediate exposure, but retention grows without bound and may retain unnecessary payment metadata/PII.

Recommended fix: document retention periods, purge or minimize processed raw bodies after the diagnostic window, and protect receipt contact fields with production database encryption/access controls.

### LOW — Report import reads the complete CSV into memory

Confidence: High  
Location: `payments/src/payments/application/daily_reports.py:97`

There is currently no public upload route, so this is not remotely exploitable. A future importer endpoint could be memory-exhausted by a large file.

Recommended fix: set an input byte limit and stream rows when report retrieval/upload is implemented.

### INFO — Secret-file ignore coverage is narrow

Confidence: High  
Location: `.gitignore:14`

`.env` and `.env.local` are ignored, but common variants such as `.env.production`, `.env.staging`, private-key, and PKCS#12 files are not covered. No such real secret files are currently tracked; committed `*.env.example` files contain placeholders/test defaults only.

## Dependency audit

- `pip-audit` with the OSV service checked installed, lock-derived environments for Auth, Catalog, Drops, Inventory, Media, Notifications, Orders, Payments, Wishlist, and the three shared Python packages: no known vulnerabilities.
- `npm audit --omit=dev` checked the frontend lock: 0 vulnerabilities.
- Local FlashMarket packages are not public registry artifacts and were reviewed as source instead.

## Secrets and exposure scan

- 786 tracked files were searched for high-confidence cloud/API tokens, private keys, authenticated database/Redis URLs, and secret-like assignments.
- Matches were limited to deployment expressions sourcing GitHub secrets/environment variables, documented examples, and test-only constants.
- No live YooKassa key, private key, cloud token, or production credential was found.

## Patch proposals

Review each patch before applying. Nothing in this section has been changed yet.

### Patch 1 — Keep ambiguous payments active

Before:

```python
locked_attempt.status = PaymentAttemptStatus.FAILED
# ...
attempt.status = PaymentAttemptStatus.EXPIRED
```

After:

```python
# A successful/unknown POST may still charge; block a second attempt.
locked_attempt.status = PaymentAttemptStatus.UNKNOWN
# ...
attempt.status = PaymentAttemptStatus.UNKNOWN
attempt.next_reconcile_at = None  # manual-review quarantine
```

Add regression tests proving that a 24-hour aged unknown operation and a malformed successful response never permit another provider POST.

### Patch 2 — Separate refund reservation from workflow status

Before:

```python
RESERVED_STATUSES = (NEW, PREPARING, UNKNOWN, PENDING, SUCCEEDED)
```

After:

```python
# Persisted on each refund and queried for balance accounting.
funds_reserved: bool
```

Set `funds_reserved=True` before the first POST and retain it for ambiguous/manual-review outcomes. Set it to `False` only for a definite rejected or canceled provider result. Add concurrency tests proving an aged unknown refund cannot free balance for a second refund.

## Coverage

- 617 source/config files and approximately 60,552 lines were included in the static pattern/data-flow pass.
- Payment authorization, provider I/O, webhook trust boundary, order events, ledger/refunds, frontend redirect/polling, migrations, deployment configuration, and observability rules were traced manually.
- This was static analysis plus automated dependency/testing checks; it does not replace DAST against a deployed test-shop environment.
