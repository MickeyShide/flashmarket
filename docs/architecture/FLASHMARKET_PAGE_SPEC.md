# FlashMarket Architecture Explorer — Page and Content Specification

**Date:** 2026-08-14
**Status:** Approved content design; UI not implemented
**Route:** `/architecture`
**Related route:** `/dev`
**Structured source:** `docs/architecture/architecture-data.js`
**Architectural source of truth:** `docs/architecture/FLASHMARKET_ARCHITECTURE_AUDIT.md`

## 1. Purpose

FlashMarket Architecture Explorer is a standalone portfolio page that explains the repository as an operating distributed system. It must serve two reading modes without maintaining two versions of the facts:

1. A portfolio visitor gets an accurate system picture in one or two minutes.
2. A Senior Backend Engineer or Tech Lead can inspect mechanisms, guarantees, limitations and source evidence.

The content path is:

```text
Overview → Service → Mechanism → Implementation details
```

The page is not an API playground and does not replace the existing `/dev` Developer Hub. `/dev` links to `/architecture`; the Architecture Explorer links back to the real API contracts in `/dev` where useful.

## 2. Success criteria

A visitor should be able to answer the following without reading source code:

- Which services exist and what data does each own?
- Which calls are synchronous and which are event-driven?
- Why are PostgreSQL, Redis and RabbitMQ used for different responsibilities?
- What does the outbox guarantee, and what does it explicitly not guarantee?
- How does Inventory prevent overselling?
- What happens on broker, consumer, Redis or external storage failure?
- Which features are complete, partial, planned or unknown?
- Where in the repository is every important claim proven?

A future UI implementation is complete only when every rendered architecture claim originates from `architecture-data.js` or a generated public contract, not from component-local prose.

## 3. Non-goals

- Do not implement the React page in this phase.
- Do not display fabricated live traffic, latency, queue depth or service status.
- Do not expose credentials, internal container addresses or private routes.
- Do not teach generic distributed-systems theory outside the real FlashMarket mechanisms.
- Do not call direct `aio-pika` workers “Celery tasks.”
- Do not claim exactly-once delivery, global ordering, distributed transactions or immediate downstream token revocation.
- Do not present mock payment confirmation or notification state transitions as real provider integrations.

## 4. Content architecture

### 4.1 Four depth levels

| Level | User intent | Content shape | Exit condition |
|---|---|---|---|
| Overview | “What is this system?” | Hero metrics, technology badges, filtered System Map | Visitor understands boundaries and chooses a path |
| Service | “What does this bounded context own?” | Responsibility, API, layers, storage, events, workers | Visitor understands one service in isolation |
| Mechanism | “How does reliability/concurrency work?” | Guided labs and end-to-end stepper | Visitor understands guarantees and trade-offs |
| Implementation details | “Prove it.” | Tables, payloads, SQL/index rationale and source evidence | Visitor can open the exact file/symbol |

### 4.2 Primary page order

```text
Hero
→ System Map
→ Service Explorer
→ Request Flow Explorer
→ Outbox Lab
→ Event Bus Explorer
→ RabbitMQ / Worker Explainer
→ Database Lab
→ Concurrency Lab
→ Consistency Map
→ Redis Explorer
→ Failure Mode Explorer
→ Why Is It Built This Way?
→ Implemented vs Planned
→ Engineering Highlights
→ Source Evidence Index
```

Desktop may keep a compact sticky section navigator after Hero. Mobile uses a section dropdown or horizontal scroll tabs rather than a permanently occupying side rail.

### 4.3 Quick paths

Hero exposes three explicit entry points:

- `Explore services` → Service Explorer.
- `Follow a request` → Request Flow Explorer.
- `Inspect reliability` → Outbox Lab.

These are navigation shortcuts, not separate copies of the content.

## 5. Shared content rules

### 5.1 Progressive disclosure

Every inspectable entity supports the same hierarchy:

```text
One-line summary
  → What / Why / Guarantee / Limitation
    → Payload, table, index or transition detail
      → Source evidence path + symbol
```

Default views show no more than one short paragraph and three to five facts per selected entity. Dense payloads, retry policy, source lists and caveats open in a detail drawer/accordion.

### 5.2 Status semantics

Status is never conveyed by color alone.

| Data value | Visible label | Meaning |
|---|---|---|
| `implemented` | `IMPLEMENTED` | Confirmed by executable code/config/migration and usually tests |
| `partial` | `PARTIAL` | A meaningful path exists, but a business or operational boundary is incomplete |
| `planned` | `PLANNED` | Documented as future work without runtime implementation |
| `unclear` | `UNCLEAR` | The repository does not prove intent or production state |

Partial and planned content must never use the same visual treatment as implemented content.

### 5.3 Content voice

- Use concrete nouns and verbs: “locks the stock row,” not “ensures seamless scalability.”
- Pair mechanism with purpose: “`(status, next_attempt_at, created_at)` matches the relay filter and oldest-first selection.”
- Name limitations next to guarantees, not in a remote disclaimer.
- Say “logical database in a shared cluster,” not “independent PostgreSQL instance.”
- Say “publisher-confirmed, at-least-once,” not “guaranteed delivery.”
- Say “current mock payment flow,” not “payment integration.”

## 6. Hero — FlashMarket System

### 6.1 Primary copy

**Title:** `FlashMarket System Architecture`

**Technical summary:**

> Nine FastAPI bounded contexts coordinate an e-commerce purchase flow through local PostgreSQL transactions, RabbitMQ choreography and deliberately non-authoritative Redis caches.

**Caveat:**

> The event/reliability platform is implemented. Real payment authority, physical notification delivery and distributed tracing remain partial or planned.

No claim should imply production scale, revenue, uptime or traffic not present in repository evidence.

### 6.2 Audited metrics

| Metric | Value | Definition shown on help/hover |
|---|---:|---|
| Microservices | 9 | Public backend services in generated registry and runtime topology |
| Logical PostgreSQL databases | 9 | One owned logical DB per backend service in one external cluster |
| Integration event types | 27 | 11 Auth identity plus 16 business events |
| Long-running workers | 16 | 7 outbox, 5 consumers, Auth cleanup, Inventory expiry, Drops scheduler, Media cleanup |
| RabbitMQ queues | 25 | 5 main, 15 per-consumer retry and 5 DLQ |
| Redis use cases | 5 | Session, touch throttle, rate limit, category cache and stock cache |
| Verified fast suites | 13 | 9 services, shared JWT, shared Rabbit reliability, gateway and frontend during audit |

`103 public API operations` may appear as a secondary fact sourced from `frontend/public/dev/services.json`; it should not compete with the distributed-system metrics.

Do not display an unstable raw test-case count. “13 verified suites” has a documented methodology and remains honest when individual parametrized cases change.

### 6.3 Technology badges

Show only technologies represented in `technologyIds`: Python 3.14, FastAPI, SQLAlchemy 2, PostgreSQL, Redis, RabbitMQ, aio-pika, Alembic, React 18, Vite, Nginx, S3/MinIO, Prometheus, Docker Compose and Ed25519 JWT.

Celery appears as a technology badge for the maintenance command layer; direct `aio-pika` remains a separate event-transport badge.

## 7. System Map

### 7.1 Default composition

The visible center contains shared infrastructure:

```text
PostgreSQL Cluster    RabbitMQ    Redis    S3 / MinIO
```

Nginx Gateway sits between Browser and the service ring. Nine service nodes surround infrastructure. Prometheus may occupy a secondary operations band; it is not part of the business request path.

### 7.2 Layer controls

| Layer | Default | Meaning |
|---|---|---|
| HTTP | on | Browser/Gateway API calls and Inventory → Drops policy call |
| Events | on | Service outbox/consumer interactions through RabbitMQ |
| Storage | off | Service → logical database and Media → S3 |
| Redis | off | Three Redis-using services |
| JWT keys | off | Auth public-key distribution to eight downstream APIs |
| Celery tasks | off | Singleton Beat, four task queues and four service-owned workers. |

Storage/Redis edges start hidden to prevent an unreadable graph. Turning on a layer does not replace the current selection.

### 7.3 Edge inspector

Hover/focus on a connection shows:

```text
FROM
TO
PROTOCOL
PURPOSE
CONTRACT
CONSISTENCY
FAILURE BEHAVIOUR
```

Click pins the inspector. Keyboard users can reach every connection through a parallel edge list; the visual graph cannot be the only access path.

### 7.4 Service selection

Selecting a service:

- highlights its incoming/outgoing HTTP and event edges;
- dims unrelated nodes rather than removing them;
- exposes counts for endpoints, published/consumed events, owned tables and workers;
- offers `Open Service Explorer`.

## 8. Service Explorer

### 8.1 Service list

The explorer contains exactly:

`Auth`, `Catalog`, `Inventory`, `Orders`, `Payments`, `Notifications`, `Wishlist`, `Drops`, `Media`.

Gateway, RabbitMQ, Redis, PostgreSQL, S3 and Prometheus are infrastructure, not microservice cards.

### 8.2 Detail template

Every service renders the same ordered sections:

1. Responsibility
2. Owns
3. Significant API
4. Actual internal layers
5. Storage
6. Publishes
7. Consumes
8. Background processes
9. Engineering decisions
10. Limitations
11. Source evidence

Empty sections are explicit. Catalog and Media display `Consumes: none`; Payments displays mock-flow limitations; Notifications displays “No physical SMTP/provider delivery.”

### 8.3 Internal structure

Do not force one architecture diagram on all services. Render layer sequences from each service’s `layerIds`.

Typical event service:

```text
API → Application → Domain → Repository/Persistence → PostgreSQL
                         ↘ Outbox → Relay → RabbitMQ
RabbitMQ → Consumer → Inbox + Local side effect (+ next Outbox)
```

Catalog:

```text
API → Application → Domain → Repository/Search → PostgreSQL
                              ↘ Category cache → Redis
```

Media:

```text
API → Application → Domain policy → PostgreSQL metadata
                                  ↘ S3 adapter
Cleanup worker → claimed metadata → S3 delete
```

### 8.4 Service-specific emphasis

| Service | First engineering detail to feature |
|---|---|
| Auth | Split signing/verification keys and row-locked refresh rotation |
| Catalog | Weighted Russian FTS + trigram and fail-open category cache |
| Inventory | Stock row lock, CHECK constraints, drop advisory lock and revision cache |
| Orders | Atomic batch checkout/promo usage plus client-authority limitation |
| Payments | Event choreography works; PSP trust boundary is mock/partial |
| Notifications | Durable projection and read state; physical delivery absent |
| Wishlist | Transactional per-user drop fan-out with unique event keys |
| Drops | Lifecycle outbox and scheduler; multi-replica due-row lock gap |
| Media | Direct S3 upload with full server-side validation and cleanup state |

## 9. Request Flow Explorer

### 9.1 Flow selector

Tabs/dropdown are populated from `flows`:

1. Register, login and rotate refresh
2. Reserve product
3. Successful checkout and payment saga
4. Payment failure compensation
5. Reservation expiration
6. Drop start to wishlist notification
7. Media upload lifecycle

The successful payment flow is visibly `PARTIAL`, because the payment trust boundary is mock. Payment failure compensation is implemented for that mock state machine.

### 9.2 Step interaction

Controls: `Previous`, `Next step`, direct numbered steps and `Restart`.

Each active step highlights one node/edge and renders:

- **What happens**
- **Why**
- **Consistency guarantee**
- **What can fail**
- **Protection**
- **View source**

The stepper never auto-advances. Motion may illustrate an event crossing a queue, but `prefers-reduced-motion` must reduce it to a state change.

### 9.3 State representation

Selected flow and step should be linkable, for example:

```text
/architecture?section=flows&flow=flow-reserve-product&step=flow-reserve-3
```

Exact router mechanics are implementation details; stable data IDs are the URL contract.

## 10. Outbox Lab

### 10.1 Primary teaching sequence

The lab starts with two side-by-side modes.

**Without Outbox**

```text
UPDATE business state
→ COMMIT PostgreSQL
→ process crash
→ RabbitMQ publish never happens
```

**With Outbox**

```sql
BEGIN;
UPDATE business_state ...;
INSERT INTO outbox_events (...);
COMMIT;
```

```text
Relay claim → publisher confirm → mark published → consumer inbox + side effect
```

### 10.2 Simulation states

`SIMULATE CRASH` in the no-outbox mode freezes after COMMIT and marks the event as permanently missing.

`WITH OUTBOX` performs the same crash after COMMIT but leaves a durable pending row. `RESTART RELAY` then claims and publishes it.

This is a deterministic educational simulation, not fabricated live telemetry. UI copy must say “simulation.”

### 10.3 Real implementation panel

Expose:

- Auth schema variant: `published_at`, `next_attempt_at`, `occurred_at`.
- Other producer schema: `status`, `next_attempt_at`, `created_at`.
- Shared fields: `attempts`, `last_error`, `claim_token`, `claimed_until`, `published_at`.
- Due indexes from `indexes`.
- `FOR UPDATE SKIP LOCKED` claim.
- Short lease, publish outside transaction, token-checked result.
- Publisher confirms, mandatory routing and five-second timeout.
- Full-jitter exponential retry capped at 300 seconds.
- At-least-once duplicate window and lack of global ordering.
- Retention limitation outside Auth.

### 10.4 Required conclusion

> Outbox removes the permanent commit/publish loss window. It does not create exactly-once delivery; FlashMarket handles the remaining duplicate window with stable event IDs and transactional consumer inboxes.

## 11. Event Bus Explorer

### 11.1 Catalog behavior

Show 27 event cards filterable by producer, consumer, status and subscriber state. Identity events with no repository subscribers remain visible and labeled `subscriber-less`; they are not silently omitted.

Selecting an event renders:

```text
Producer → flashmarket.events → routing key → queue(s) → consumer(s)
```

and fields:

- Event name
- Producer
- Trigger
- Payload fields
- Exchange
- Routing key
- Queues
- Consumers
- Side effects
- Retry
- Idempotency
- Delivery semantics
- Source evidence

### 11.2 Multi-consumer behavior

For `OrderCreated`, `PaymentSucceeded`, `PaymentFailed` and `OrderCancelled`, render one branch per consumer queue. Make clear that one queue’s retry does not rebroadcast to successful queues.

### 11.3 Contract caveat

Auth uses a versioned envelope. Most business events are flat JSON without `schema_version`. The explorer labels event contract governance `PARTIAL`; it must not invent schemas or versions.

## 12. RabbitMQ / Worker Explainer

### 12.1 Required distinction

```text
RabbitMQ = broker and routing/durability boundary
Celery = periodic command execution framework
FlashMarket = RabbitMQ integration events through aio-pika plus isolated Celery maintenance commands
```

The page must render the actual `Beat → RabbitMQ /flashmarket-tasks → service Celery worker` chain, not route normal API requests or integration events through Celery.

### 12.2 Actual chain

```text
API / consumer / scheduler
→ local PostgreSQL transaction + outbox
→ Python outbox relay (aio-pika)
→ RabbitMQ
→ Python consumer (aio-pika)
→ local PostgreSQL inbox + side effect
```

### 12.3 Worker inventory

Show 16 long-running process cards grouped by role:

- 7 outbox relays
- 5 event consumers
- Auth cleanup
- Inventory expiry
- Drops scheduler
- Media cleanup

Show Auth key generation separately as a one-shot startup process.

Every worker card uses:

`trigger`, `sideEffect`, `retry`, `timeout/health`, `idempotency`, `status`.

### 12.4 Queue topology

Each of five queue families expands to:

```text
main
├── retry.1 — 5 seconds
├── retry.2 — 30 seconds
├── retry.3 — 120 seconds
└── dlq
```

Include main/retry and DLQ capacity policies, ACK ordering and manual guarded replay. Do not imply automatic DLQ repair.

## 13. Database Lab

### 13.1 Service selector

The selector displays nine logical databases and their 32 owned tables. The shared PostgreSQL cluster is visible as deployment topology, while ownership remains per service.

### 13.2 Query/index case template

```text
QUERY
INDEX
WHY THIS ORDER
WITHOUT THE INDEX
LIMITATION (when applicable)
SOURCE
```

Use simplified SQL matching a real repository predicate; label it “simplified” rather than presenting generated SQL as exact.

### 13.3 Featured cases

1. **Outbox due work**

   ```sql
   SELECT ... FROM outbox_events
   WHERE status IN ('pending', 'failed')
     AND next_attempt_at <= now()
   ORDER BY created_at
   FOR UPDATE SKIP LOCKED
   LIMIT 1;
   ```

   Index: `(status, next_attempt_at, created_at)`.

2. **Reservation expiry**

   Query filters `status='RESERVED'` and `expires_at <= now()`.
   Index: `(status, expires_at)`.

3. **Catalog search**

   Weighted Russian FTS GIN plus name trigram GIN fallback.

4. **Media cleanup**

   `(status, upload_expires_at)` and `(status, delete_requested_at)`.

5. **Audit investigation**

   `(event_type, created_at)`, `(actor_user_id, created_at)`, `(subject_user_id, created_at)`.

6. **Promotion user limit**

   `(promocode_id, user_id)` plus unique usage constraints.

### 13.4 Integrity caveats

Show database gaps beside successes:

- `(product_id, variant_id)` does not make `(product_id, NULL)` unique under normal PostgreSQL NULL semantics.
- `orders.reservation_id` and `payments.order_id` are indexed, not unique.
- No partial index currently exists.
- Inventory `revision` is cache freshness, not SQL optimistic concurrency.

## 14. Concurrency Lab

### 14.1 Overselling race

Start with the unsafe timeline:

```text
stock = 1

User A                 User B
read available=1       read available=1
reserve                reserve
```

Then reveal the implemented timeline:

```text
User A: SELECT stock FOR UPDATE ─ mutate ─ COMMIT
User B: waits ─ reads committed available=0 ─ rejects
```

Show database CHECK constraints as a second line of defense, not as the primary serialization mechanism.

### 14.2 Additional cases

| Case | Mechanism | Status |
|---|---|---|
| Per-user drop limit | `pg_advisory_xact_lock(user, drop)` | Implemented |
| Reservation expiry workers | `FOR UPDATE SKIP LOCKED` | Implemented |
| Outbox relay replicas | short claim lease + `SKIP LOCKED` | Implemented; duplicates still possible |
| Refresh rotation | refresh/session/user row lock | Implemented |
| Promocode usage | promo row lock + unique usage | Implemented |
| Duplicate order/payment create | application check without unique command boundary | Partial |
| Drops scheduler replicas | state check without due-row lock | Partial |
| Wishlist/Media caps | count-before-insert without per-user serialization | Partial |

Every case uses `Race → Protection → Invariant → Remaining limitation`.

## 15. Consistency Map

Render five explicit boundaries:

1. **Strong local consistency** — one service PostgreSQL transaction.
2. **Eventual inter-service consistency** — RabbitMQ choreography.
3. **At-least-once delivery** — relay/consumer duplicate window.
4. **Bounded-stale cache consistency** — Catalog/Inventory Redis.
5. **Eventual downstream auth revocation** — local JWT accepted until expiry.

The primary diagram should place a boundary around each service database and show no transaction line crossing two services.

Required explanation:

> FlashMarket preserves hard invariants inside the owning database. Between services it exchanges durable facts and accepts temporary divergence. Inbox/state guards make repeated facts converge, while unresolved monetary compensation remains explicitly partial.

## 16. Redis Explorer

Use five cards, not generic categories that imply absent features:

1. Active session marker
2. Session-touch throttle
3. Auth rate-limit counter
4. Catalog category-tree cache
5. Inventory stock cache

Each card shows:

`KEY`, `VALUE`, `TTL`, `WRITER`, `READER`, `INVALIDATION`, `FAILURE BEHAVIOUR`, `SOURCE`.

Include an explicit negative-facts panel:

- Redis is not the stock lock.
- Redis is not reservation authority.
- Redis is not consumer idempotency storage.
- Redis is not the outbox claim lock.
- Redis is not the drop-limit distributed lock.

## 17. Failure Mode Explorer

Populate the selector from all `failureScenarios`. Recommended first five:

- What if RabbitMQ is unavailable?
- What if a consumer receives the same event twice?
- What if two users buy the last item?
- What if a worker crashes after commit?
- What if Redis is unavailable?

Detail format:

```text
PROBLEM
MECHANISM
RESULT
REMAINING LIMITATION
SOURCE
```

Failures with unresolved business compensation, missing HTTP idempotency or schema governance use `PARTIAL`. A green “resolved” state must not be shown when a remaining limitation is material.

## 18. Interview Mode — Why Is It Built This Way?

The section is a concise interview worksheet backed by `interviewQuestions`.

Cards:

- Why microservices here?
- Why not publish directly after commit?
- What exactly does Outbox guarantee?
- Why Celery only for periodic commands, while integration events stay on `aio-pika`?
- Why RabbitMQ?
- Why Redis?
- Why this outbox index order?
- Where is the transaction boundary?
- How is overselling prevented?
- What happens with duplicate events?
- What happens if a service is down?
- Why is eventual consistency acceptable?
- Why use both a lock and a constraint?

Each card starts with `shortAnswer`. `deepAnswer` expands on click and ends with evidence. Answers must include trade-offs; no answer may imply that a chosen technology is universally superior.

## 19. Implemented vs Planned

### 19.1 Implemented examples

- Nine data-owning services and local JWT authorization
- Transactional outbox/inbox
- Publisher confirms, retry queues and DLQs
- PostgreSQL stock locking and constraints
- Drop-targeted wishlist fan-out
- Direct S3 uploads with validation
- Structured metrics/logging and worker heartbeat

### 19.2 Partial examples

- Payment flow: mock self-confirmation and client-provided commercial snapshot
- Notifications: durable state without physical delivery
- Event contracts: flat unversioned payloads outside Auth
- Distributed traceability: request/event IDs are not one trace
- Scheduler/idempotency/quota boundaries documented in audit

### 19.3 Planned or unclear

- Real PSP/webhook/refund/reconciliation
- Physical SMTP/provider delivery
- OpenTelemetry distributed tracing
- Secret manager and automated secret scanning
- RabbitMQ clustering/quorum/DR state is unclear from this repository
- Celery maintenance is implemented; event consumers and outbox relays deliberately remain outside it

Do not place planned nodes on the implemented System Map unless a “show future” control is explicitly enabled.

## 20. Engineering Highlights

Render the ranked 15 highlights from `engineeringHighlights`. Each card includes:

- concrete mechanism;
- why it matters;
- mechanism/source link;
- status.

The list is already ordered for interview relevance. It must not be reordered by visual novelty alone.

## 21. Source Evidence

### 21.1 Evidence object

Each evidence record contains:

```js
{
  id,
  path,
  symbol,
  description
}
```

### 21.2 View source behavior

Deep-dive cards show at least:

```text
FILE
SYMBOL
WHAT THIS PROVES
```

The first UI version may copy a path rather than open an external repository URL. No fake line number should be generated. If repository links are later added, their base revision must correspond to the audited commit or visibly state that links follow `main`.

### 21.3 Evidence density

Overview cards do not show paths by default. Service and mechanism detail shows one primary source; the full evidence drawer shows all `evidenceIds`.

## 22. Structured data model

`architecture-data.js` exports `architectureData` and `ARCHITECTURE_STATUS` as a framework-independent ES module.

Top-level collections:

```text
meta
system
statuses
technologies
services
infrastructure
connections
endpoints
events
exchanges
queues
workerProcesses
oneShotProcesses
celeryTasks
databases
tables
constraints
indexes
redisUseCases
mechanisms
flows
consistencyBoundaries
failureScenarios
interviewQuestions
engineeringHighlights
plannedCapabilities
evidence
projections
```

### 22.1 Identity and reference rules

- IDs are globally stable kebab-case identifiers.
- Relationships use IDs; embedded copies of services/events/tables are forbidden.
- Display ordering comes from array order or explicit `rank`, never from ID parsing.
- `evidenceIds` is the only source-evidence relationship.
- Entity status uses only the four declared status values.
- Empty truth is preserved: `celeryTasks: []` is meaningful data.
- Computed queue families are allowed only when they emit stable explicit queue objects.

### 22.2 Audited snapshot policy

Counts in `heroStats` are an audited snapshot dated in `meta.auditedAt`. Future implementation should provide a validation script/test that checks:

- unique IDs;
- every reference resolves;
- counts equal collection lengths or documented methodology;
- every implemented mechanism/event/service has evidence;
- 15 highlight ranks are unique and contiguous;
- queue family count remains 5 main + 15 retry + 5 DLQ;
- `celeryTasks` contains the four runtime task registrations and their Beat schedules.

Generated public OpenAPI remains authoritative for the complete endpoint catalog. `architecture-data.js` contains only architecture-significant endpoint groups.

## 23. Responsive and accessible behavior

These are requirements for the future UI, not implementation in this phase.

- Every graph has an equivalent list/table representation.
- Hover behavior is also available through keyboard focus and click/tap.
- Status, protocol and guarantee are expressed in text, not color alone.
- Focus order follows page/content order; opening a detail panel moves focus predictably and closing returns it.
- Motion honors `prefers-reduced-motion`.
- Flow steppers remain manually controlled.
- Mobile replaces dense graph canvases with node lists and step cards; no horizontal page overflow is required to understand a flow.
- Payload, SQL and key patterns use selectable text with wrapping/scroll contained inside their panel.

## 24. Content state and linking

The future page may encode these stable selections in URL search/hash state:

- current section;
- selected service;
- selected flow and step;
- selected event;
- active map layers;
- selected failure scenario.

State must be derived from entity IDs and validated against the data module. An unknown ID falls back to the section default without breaking the page.

No architecture interaction changes backend state. All labs and crash controls are deterministic client-side explanations.

## 25. Verification plan for the future UI

### Data contract tests

- Import the module successfully as ESM.
- Validate global ID uniqueness and all references.
- Assert audited collection counts.
- Assert each service has responsibility, ownership, database, status and evidence.
- Assert each routed event resolves producer, exchange, queues and consumers.
- Assert every flow step resolves its node and contains all five explanatory fields.
- Assert all four Celery task cards, owner services, queues and schedules are rendered.

### Content tests

- Hero values match `heroStats` exactly.
- Payments and Notifications never lose their `PARTIAL` status.
- Eventual/at-least-once labels appear on event flows.
- Outbox simulation distinguishes permanent loss from durable recovery.
- Redis explorer distinguishes fail-open cache from fail-closed Auth state.
- Planned capabilities are hidden from the implemented map by default.
- Source drawer displays real path and symbol.

### Interaction tests

- Map layers filter edges without deleting the selected entity.
- Service/event/flow deep links restore selection.
- Flow previous/next boundaries work.
- Keyboard interaction reaches every graph-equivalent item.
- Reduced-motion mode has no required animated transition.
- Mobile list view exposes the same facts as desktop graph view.

## 26. Implementation handoff

The future implementation should consume the existing module rather than rewrite it into component files. Suggested component boundaries, without prescribing a styling system:

```text
ArchitecturePage
├── ArchitectureHero
├── SystemMap + ConnectionInspector + MapEdgeList
├── ServiceExplorer
├── FlowExplorer
├── MechanismLab (Outbox / Database / Concurrency / Redis)
├── EventBusExplorer
├── ConsistencyMap
├── FailureExplorer
├── InterviewMode
├── StatusMatrix
└── EvidenceDrawer
```

Before UI work begins, review `architecture-data.js` against the current repository revision. If production code changes, update the audit/data first; the page should remain a projection of source truth rather than an independently maintained architecture story.

## 27. Definition of done for this content phase

- `FLASHMARKET_PAGE_SPEC.md` defines the complete page hierarchy, content, interaction and truthfulness rules.
- `architecture-data.js` contains normalized referenced entities rather than component-local duplication.
- The data module imports successfully and audited counts match the approved definitions.
- Every implemented claim can resolve to source evidence.
- Celery, payment, notification and tracing status is represented honestly.
- No UI or production code is changed.
- No unfinished markers or intentionally blank decisions remain.
