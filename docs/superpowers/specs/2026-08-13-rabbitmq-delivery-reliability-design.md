# RabbitMQ Delivery Reliability Design

## Context

FlashMarket exchanges purchase-saga, notification, and drop events through the
durable `flashmarket.events` topic exchange in the shared `/flashmarket` vhost.
The shared-vhost fix makes cross-service routing possible, but the current
delivery behavior can still lose events or amplify an outage:

- Inventory, Orders, Payments, Notifications, and Wishlist reject failed
  messages without requeueing, and their queues have no dead-letter target.
- Outbox relays publish with `mandatory=False`, so an unroutable message can be
  marked as published even though no queue received it.
- Inventory, Orders, Payments, Notifications, and Drops immediately select a
  failed outbox row again, creating a hot PostgreSQL/RabbitMQ/logging loop.
- Only Wishlist retries an initial RabbitMQ connection without exiting.
- Worker containers have no health signal beyond process existence.
- Queue growth is not bounded, which can turn a stopped consumer into broker
  memory or disk exhaustion on the four-GiB production host.

The project already uses transactional outboxes for domain changes and makes
most consumer handlers idempotent. This package completes the message-delivery
boundary without changing business workflows or introducing a RabbitMQ plugin.

## Goals

- Provide at-least-once delivery from an outbox relay to a successfully handled
  consumer message.
- Retry transient consumer failures three times with bounded delays, then
  retain the message in a dead-letter queue.
- Route permanently malformed messages directly to a dead-letter queue.
- Prevent silent success for unroutable outbox events.
- Prevent failed outbox rows and connection failures from creating hot loops.
- Bound queue growth and make stalled workers visible to Docker and monitoring.
- Preserve existing main queue names and accumulated messages during rollout.

## Non-goals

- Exactly-once delivery. A crash after a database commit but before message ACK
  can cause redelivery, so business handlers must remain idempotent.
- A browser-based DLQ administration interface.
- Automatic replay or deletion of dead-lettered messages.
- RabbitMQ clustering, quorum-queue migration, Federation, Shovel, or the
  delayed-message plugin.
- Changing the purchase-saga business state machine.
- Redefining the Gateway's local `/health` endpoint as aggregate readiness.

## Considered Approaches

### In-process sleep followed by requeue

The consumer could sleep before rejecting a message with requeue enabled. This
is simple but occupies a worker slot, prevents useful messages behind the failed
one from progressing, and can create a hot requeue cycle after restarts.

### RabbitMQ delayed-message plugin

The delayed-message exchange provides convenient scheduling. It requires a new
broker plugin, deployment coordination with the external observability stack,
and another compatibility surface on a memory-constrained host.

### Per-consumer TTL retry queues

Use ordinary durable queues with per-queue TTL and dead-letter routing. This is
supported by the existing RabbitMQ installation, does not block consumers, and
keeps retries isolated to the consumer that failed. This is the selected
approach.

## Shared Reliability Package

Create `shared/rabbitmq_reliability` as a small installable Python package. It
owns only transport-level behavior:

- durable queue and exchange declaration;
- retry/DLQ topology naming and arguments;
- message classification and retry attempt metadata;
- confirmed publishing with mandatory routing and a finite timeout;
- initial-connect and clean-exit retry with exponential backoff and jitter;
- worker heartbeat updates and checks;
- common RabbitMQ delivery metrics.

It does not import service models, repositories, settings, or business
handlers. Each service supplies its queue name, routing keys, handler callable,
and configuration. Dockerfiles copy and install the package in the same manner
as `shared/jwt_verifier` where required.

The package targets the service-supported `aio-pika` 9.x API. Auth uses
`aio-pika` 10 only for its outbox and consumes the shared confirmed-publish
contract through the common API surface supported by both major versions.

## Consumer Topology

Each consumer keeps its current durable main queue:

- `inventory.events`
- `orders.events`
- `payments.events`
- `notifications.events`
- `wishlist.drop-events`

For main queue `<queue>`, declare:

- `<queue>.retry.1`, message TTL 5,000 ms;
- `<queue>.retry.2`, message TTL 30,000 ms;
- `<queue>.retry.3`, message TTL 120,000 ms;
- `<queue>.dlq`, without an automatic expiry.

Retry queues dead-letter expired messages to a dedicated direct retry exchange,
which routes them back to that consumer's main queue. A consumer failure
publishes a copy to the next retry queue and acknowledges the source message
only after publisher confirmation. Per-consumer retry queues are used instead
of republishing to the shared topic exchange so that one consumer's failure
does not cause successful consumers to receive the event again.

The copied message preserves body, content type, message ID, type, timestamp,
correlation ID, and non-transport headers. It adds transport headers:

- `x-flashmarket-attempt`: `1`, `2`, or `3` for a scheduled retry;
- `x-flashmarket-original-routing-key`: the original topic routing key;
- `x-flashmarket-failure-kind`: stable classification value;
- `x-flashmarket-last-error`: a sanitized, truncated error description.

After a message has returned from retry attempt 3, another transient failure
publishes it to `<queue>.dlq`. Thus every message receives one initial handling
attempt plus three delayed retries. The DLQ message retains the attempt metadata
and failure description.

## Error Classification and ACK Rules

Transport code distinguishes two handler outcomes:

- `PermanentMessageError`: invalid UTF-8/JSON, invalid UUID, absent required
  fields, unsupported schema version, or another payload defect that cannot be
  corrected by waiting. Publish directly to DLQ.
- Any other handler exception: treat as transient and schedule the next retry,
  or DLQ after retry 3.

Each service converts known parsing and validation failures into
`PermanentMessageError`. Unexpected database, Redis, RabbitMQ, timeout, and
dependency exceptions remain transient.

The ACK sequence is strict:

1. Run the business handler transaction.
2. On success, ACK the original message.
3. On failure, publish the failure copy to retry or DLQ with publisher confirms,
   mandatory routing, returned-message exceptions, and a finite timeout.
4. ACK the original only after the failure copy is confirmed.
5. If publishing the failure copy fails, reject the original with `requeue=True`.

This can cause a duplicate failure copy if the broker accepted it but the
confirmation was lost. It cannot silently discard the only copy. DLQ inspection
and replay tooling must therefore treat `message_id` as an idempotency key.

## Queue Bounds and Overflow

Main and retry queues receive configurable limits with conservative defaults:

- main queue maximum length: 20,000 messages;
- main queue maximum bytes: 128 MiB;
- retry queue maximum length: 5,000 messages per stage;
- retry queue maximum bytes: 32 MiB per stage;
- overflow mode: `reject-publish-dlx` where supported by the installed RabbitMQ
  version.

A dedicated dead-letter exchange routes overflow from a main or retry queue to
that consumer's DLQ. The DLQ is not assigned a destructive maximum length or
TTL in this package: silently dropping the oldest failure would contradict the
retention goal. Operators instead alert on any DLQ message and on queue depth.
The limits are environment-configurable for later tuning.

Existing queues may have been declared without these immutable arguments.
Redeclaring them with different arguments would raise `PRECONDITION_FAILED`.
Deployment must therefore apply a RabbitMQ policy to existing main queues for
maximum length, maximum bytes, overflow, and dead-letter settings before new
consumers declare them. Retry and DLQ queues are new and can be declared with
their full arguments. The bootstrap is idempotent and failure to apply the
policy is fatal.

## Confirmed Publishing

All outbox relays open channels with:

- publisher confirms enabled;
- returned messages raised to the caller;
- `mandatory=True` for every event;
- a configurable publish timeout, default five seconds.

An event is marked published only after a positive confirmation. An unroutable
message, broker NACK, channel failure, or timeout remains pending with diagnostic
state. Consumers use the same confirmed-publish helper when moving a failed
message into retry or DLQ.

Wishlist's `DropStarted` fan-out currently publishes notification events inside
the inbound message handler. This package moves that fan-out to a Wishlist
transactional outbox so a partial publish cannot lose the remaining users. A
unique `event_key` per drop and user is stored on the Wishlist outbox row and
enforced by a database constraint, so redelivery of `DropStarted` cannot create
duplicate pending fan-out rows. The same key remains the downstream idempotency
boundary at Notifications. The Wishlist outbox uses the same confirmed relay
behavior as other services.

## Outbox Retry Model

Inventory, Orders, Payments, Notifications, Drops, and the new Wishlist outbox
share these nullable delivery-control fields:

- `next_attempt_at`;
- `last_error`;
- `claimed_until`;
- `claim_token`.

Existing `attempts` and published/status fields remain compatible. Migrations
add only nullable columns and supporting pending-work indexes; they do not
rewrite, delete, or mark existing rows published.

Selection includes only unpublished rows whose `next_attempt_at` is null or due.
After a failure:

- increment `attempts`;
- record a sanitized error capped at 1,000 characters;
- set `next_attempt_at` using exponential backoff with full jitter, capped at
  five minutes;
- leave the row eligible for a future retry.

After confirmation:

- set published state/time;
- increment `attempts`;
- clear `next_attempt_at` and `last_error`.

Each event is claimed and published independently rather than holding one
transaction and row locks while publishing an entire batch. A short claim lease
prevents two relay replicas from deliberately publishing the same row, while an
expired lease allows recovery after a crash. Because confirmation and SQL state
cannot be one atomic transaction, a crash can still publish the same event
twice. Stable event/message IDs and idempotent consumers handle that expected
at-least-once case.

If a batch contains only failed events scheduled for later, the worker sleeps
for its poll interval instead of immediately selecting them again.

## Connection Recovery

Inventory, Orders, Payments, Notifications, and Wishlist consumers use a common
outer reconnect loop. `connect_robust` continues to restore an established
connection; the outer loop handles initial failure and an unexpected clean
return.

Backoff starts at one second, doubles to a maximum of 30 seconds, and applies
jitter. A successful connected interval resets it. Cancellation always exits
promptly. Outbox workers use the same policy.

## Worker Health and Observability

Consumer, outbox, scheduler, expiry, and cleanup processes write an atomic
heartbeat file in a per-container temporary directory. Heartbeat content records
the UTC wall-clock timestamp and phase:

- consumers run a lightweight periodic heartbeat task after topology
  declaration, so a correctly idle queue remains healthy; receipt and handling
  also update the phase for diagnostics;
- outbox workers update after each successful poll cycle, including an empty
  cycle;
- maintenance workers update after each completed tick, including zero work.

Docker healthchecks run a small shared command that verifies the file exists and
is newer than a role-specific threshold. Startup grace accommodates migrations
and initial broker recovery. A process that is alive but no longer completing
work becomes unhealthy. A broker outage can therefore make a consumer unhealthy
without causing restart churn; alerts distinguish dependency failure from
process exit.

Expose Prometheus metrics where the existing multiprocess setup permits:

- `flashmarket_rabbitmq_retries_total{service,queue,attempt}`;
- `flashmarket_rabbitmq_dlq_total{service,queue,reason}`;
- `flashmarket_rabbitmq_publish_failures_total{service,kind}`;
- `flashmarket_worker_last_success_timestamp_seconds{service,role}`;
- `flashmarket_outbox_oldest_pending_age_seconds{service}`.

RabbitMQ-native queue depth and consumer-count alerts remain broker/exporter
metrics. Alert on any DLQ depth, no consumer on a main queue, sustained main
queue growth, old pending outbox rows, and stale worker heartbeat.

Gateway `/health` remains the liveness check for Nginx itself. Aggregate backend
readiness is intentionally not added to it because making Gateway health depend
on every microservice would restart or withdraw a healthy routing tier during a
single-service outage. Per-service readiness remains under `/dev/status/*`.

## Configuration

Shared defaults are configurable through service-prefixed environment settings:

- publish timeout: 5 seconds;
- retry delays: 5, 30, and 120 seconds;
- reconnect initial/max delay: 1/30 seconds;
- main/retry queue message and byte limits;
- heartbeat path, periodic interval, and stale thresholds;
- outbox maximum backoff: 300 seconds;
- outbox claim lease duration.

Environment examples document the values, while common helpers validate that
retry delays are positive and ordered and that heartbeat thresholds exceed the
normal poll interval.

## Database and Topology Migration

Deployment order for each service is:

1. Build the image containing the shared reliability package.
2. Apply additive database migrations.
3. Apply the idempotent RabbitMQ policy for existing main queues and verify the
   shared exchange/vhost permissions.
4. Start the updated consumer, which creates retry/DLQ topology.
5. Start the updated outbox relay.
6. Start updated maintenance workers and API where needed.
7. Verify queue bindings, consumer counts, heartbeats, pending outbox age, and
   DLQ depth before moving to the next service.

Consumers are updated before relays so newly published events always have their
target topology. Existing main queue names and their contents are retained.
Retry and DLQ queues are additive. No deployment step purges or deletes a queue.

## Testing

### Unit tests

- permanent versus transient classification;
- attempt header parsing and bounds;
- retry delay selection and transition to DLQ;
- failure-copy property preservation;
- ACK only after confirmed retry/DLQ publish;
- requeue when failure-copy publishing fails;
- reconnect backoff reset, jitter bounds, clean-return retry, and cancellation;
- outbox backoff/claim expiry and heartbeat freshness.

### Repository contracts

- all five consumers use the common topology and reconnect helpers;
- all outbox publishers use mandatory confirmed publishing with a timeout;
- production worker containers have healthchecks;
- queue names, retry delays, and policy patterns are unique and consistent;
- migrations and environment examples cover every outbox service.

### RabbitMQ integration tests

- a transient error receives an initial attempt and three delayed retries, then
  appears in DLQ;
- malformed JSON goes directly to DLQ;
- a failure to publish the retry copy requeues the original;
- an unroutable mandatory outbox publish is not recorded as delivered;
- consumer and relay recover after broker unavailability;
- queue overflow routes rejected publications into DLQ on the production
  RabbitMQ version.

Existing service, saga, Compose-render, lint, and type-check suites remain
required regression coverage.

## Rollout Verification

For every service, record before and after:

- main/retry/DLQ queue message counts and consumers;
- oldest pending outbox age and attempts;
- container restart count and health;
- publish-return/NACK/timeout metrics;
- RabbitMQ memory, disk alarm, and connection count.

Inject one synthetic transient failure and one malformed event in staging. The
transient event must follow the configured delays and end in DLQ after retry 3;
the malformed event must enter DLQ immediately. No production queue is purged
as part of verification.

## Rollback

Roll back containers in reverse order: outbox relays, consumers, then
maintenance workers. Additive nullable columns remain in place. Retry exchanges,
retry queues, DLQs, and non-destructive policies may also remain because old
workers ignore them.

If the queue policy itself causes an incident, restore the previous named policy
definition rather than deleting queues. Never purge retry or DLQ contents during
rollback. Messages accumulated there are operator-visible evidence and require
an explicit replay or disposition decision.

## Acceptance Criteria

- No consumer exception can silently discard the only copy of a message.
- Permanent failures enter the consumer DLQ without retry.
- Transient failures receive exactly three scheduled retry opportunities before
  DLQ under normal confirmations.
- An unroutable outbox event remains unpublished and retryable.
- Failed outbox rows cannot form a no-sleep hot loop.
- Initial RabbitMQ outages do not produce Docker restart churn.
- Main and retry queue growth is bounded without silently dropping overflow.
- Every background process exposes a stale-work health signal.
- Existing main queues and queued messages survive rollout and rollback.
