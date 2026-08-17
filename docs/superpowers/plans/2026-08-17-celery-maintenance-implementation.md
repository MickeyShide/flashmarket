# Celery Maintenance Layer Implementation Plan

1. Add `shared/celery_runtime` with the app factory, singleton Beat schedule, async runner, and unit tests.
2. Add the shared dependency and Celery task module to Auth; extract cleanup into a reusable one-shot operation.
3. Add the task module to Inventory and close its async Redis/SQLAlchemy resources on child shutdown.
4. Convert Drops scheduler to a one-shot operation, add due-row locking, and expose it as a Celery task.
5. Add the Media cleanup task and child resource shutdown.
6. Add Celery roles to the entrypoint and copy/install the shared package in all four images.
7. Split RabbitMQ task-vhost initialization from event-topology initialization.
8. Replace loop services in service/root Compose files and add singleton Beat persistence.
9. Regenerate all affected `uv.lock` files.
10. Run focused and full tests, render Compose, and update the architecture audit/explorer to the new runtime truth.
