import asyncio
import threading

from flashmarket_celery.app import QUEUES, TASK_ROUTES, create_app
from flashmarket_celery.async_runner import AsyncRunner


def test_app_declares_isolated_routes_and_reliable_delivery() -> None:
    app = create_app("test")

    assert {queue.name for queue in app.conf.task_queues} == set(QUEUES)
    assert app.conf.task_routes == TASK_ROUTES
    assert app.conf.task_acks_late is True
    assert app.conf.task_reject_on_worker_lost is True
    assert app.conf.worker_prefetch_multiplier == 1
    assert app.conf.task_ignore_result is True


def test_async_runner_reuses_one_event_loop_thread() -> None:
    runner = AsyncRunner()

    async def identity() -> tuple[int, int]:
        return id(asyncio.get_running_loop()), threading.get_ident()

    first = runner.run(identity())
    second = runner.run(identity())
    runner.shutdown()

    assert first == second
    assert first[1] != threading.get_ident()


def test_async_runner_runs_cleanup_before_shutdown() -> None:
    runner = AsyncRunner()
    cleaned = threading.Event()

    async def cleanup() -> None:
        cleaned.set()

    runner.run(asyncio.sleep(0))
    runner.shutdown(cleanup())

    assert cleaned.is_set()
