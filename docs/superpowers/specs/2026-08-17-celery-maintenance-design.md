# Celery Maintenance Layer Design

## Scope

Move the four polling maintenance processes to Celery:

- Auth expired-data cleanup
- Inventory reservation expiry
- Drops lifecycle scheduling
- Media asset cleanup

Integration-event consumers and transactional outbox relays remain on `aio-pika`. Celery is a command-job layer, not the domain-event bus.

## Topology

RabbitMQ uses a separate `/flashmarket-tasks` vhost. One singleton Celery Beat publishes to four durable queues:

| Queue | Task | Default interval |
| --- | --- | --- |
| `auth.maintenance` | `flashmarket.auth.cleanup_expired_data` | 3600 seconds |
| `inventory.maintenance` | `flashmarket.inventory.expire_reservations` | 5 seconds |
| `drops.maintenance` | `flashmarket.drops.run_scheduler_tick` | 10 seconds |
| `media.maintenance` | `flashmarket.media.cleanup_expired_assets` | 30 seconds |

Each service image runs only its own task module and consumes only its own queue. Workers initially run with prefork concurrency 1 and prefetch 1. Task results are ignored.

The singleton Beat process runs from the Auth image but imports only the shared scheduling package. It knows task names, routing keys, and intervals; it does not import another service or access another database.

## Async runtime

The services use async SQLAlchemy, asyncpg, and, for Inventory, async Redis. Celery tasks are synchronous entry points. A small shared package owns one lazy, persistent asyncio event loop thread per prefork child. The task blocks on `run_coroutine_threadsafe`, so a service's async clients remain bound to one loop for the lifetime of that child.

Celery child-shutdown signals dispose service-owned engines and Redis clients before stopping the loop. No event loop or connection is created in the prefork parent.

## Delivery and correctness

Maintenance tasks use late acknowledgement and reject-on-worker-loss. A killed child therefore causes RabbitMQ redelivery. Routine task failures are recorded by Celery and recovered by the next Beat tick rather than creating an overlapping retry storm.

Every operation is safe to run more than once:

- Auth deletes records behind time predicates.
- Inventory claims expired reservations with `FOR UPDATE SKIP LOCKED` and changes guarded status rows transactionally with its outbox event.
- Media claims cleanup candidates with database row locking and status guards.
- Drops will add `FOR UPDATE SKIP LOCKED` to due-row queries so concurrent or redelivered ticks cannot create duplicate transition events.

Beat must remain a singleton. Database locking is still required because broker redelivery and task overlap are normal distributed-system behavior.

## Operations

Compose replaces the four loop containers with four Celery worker containers and adds `celery-beat`. The shared entrypoint gets `celery-worker` and `celery-beat` roles, setting the process role before exec.

The infrastructure initializer creates the task vhost and permissions without installing integration-event retry/DLQ topology there. Celery declares its queues and exchanges.

Worker healthchecks use Celery ping addressed to the local nodename. Existing service metrics and heartbeat files remain available for task-progress monitoring where applicable. Beat persists its schedule in a named volume and must have exactly one running replica.

## Configuration

`CELERY_BROKER_URL` defaults to the existing RabbitMQ host with vhost `/flashmarket-tasks`. Schedule intervals are environment-configurable:

- `CELERY_AUTH_CLEANUP_INTERVAL_SECONDS`
- `CELERY_INVENTORY_EXPIRY_INTERVAL_SECONDS`
- `CELERY_DROPS_SCHEDULER_INTERVAL_SECONDS`
- `CELERY_MEDIA_CLEANUP_INTERVAL_SECONDS`

Production TLS and credentials follow the same RabbitMQ policy as the event vhost.

## Verification

Unit tests cover the shared async runner, Celery configuration/routing, each task's one-shot behavior, and Drops row locking. Existing service suites verify domain behavior. Compose configuration is rendered as a final static check.
