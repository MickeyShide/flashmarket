"""Drops maintenance tasks."""

from celery import signals  # type: ignore[import-untyped]
from flashmarket_celery import AsyncRunner
from rabbitmq_reliability import ensure_worker_metrics_server, touch_heartbeat

from drops.celery_app import app
from drops.infrastructure.database import engine
from drops.scheduler import run_scheduler_tick

runner = AsyncRunner()


async def run_scheduler_once() -> None:
    """Advance every due Drop lifecycle row once."""
    await run_scheduler_tick()
    touch_heartbeat("/tmp/flashmarket-heartbeat.json", "drops_scheduler")


@app.task(  # type: ignore[untyped-decorator]
    name="flashmarket.drops.run_scheduler_tick",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
    acks_late=True,
)
def run_scheduler_task() -> None:
    """Celery entry point for the Drops lifecycle scheduler."""
    runner.run(run_scheduler_once())


@signals.worker_process_init.connect  # type: ignore[untyped-decorator]
def initialize_worker_process(**_: object) -> None:
    """Expose worker progress metrics before the first scheduled task."""
    ensure_worker_metrics_server()


@signals.worker_process_shutdown.connect  # type: ignore[untyped-decorator]
def shutdown_worker_process(**_: object) -> None:
    """Dispose the child-owned async SQLAlchemy pool."""
    runner.shutdown(engine.dispose())
