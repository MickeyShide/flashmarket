"""Run async service code safely from synchronous Celery prefork tasks."""

from __future__ import annotations

import asyncio
import os
import threading
from collections.abc import Coroutine
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Any, TypeVar

T = TypeVar("T")


class AsyncRunner:
    """Own one lazy event-loop thread in each worker child process."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._pid: int | None = None

    def run(self, coroutine: Coroutine[Any, Any, T], *, timeout: float | None = None) -> T:
        """Run a coroutine on the process-local persistent loop."""
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coroutine, loop)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            future.cancel()
            raise

    def shutdown(self, cleanup: Coroutine[Any, Any, object] | None = None) -> None:
        """Run optional async cleanup, then stop the loop thread."""
        with self._lock:
            loop = self._loop
            thread = self._thread
            pid = self._pid

        if loop is None or thread is None or pid != os.getpid():
            if cleanup is not None:
                cleanup.close()
            return

        if cleanup is not None:
            asyncio.run_coroutine_threadsafe(cleanup, loop).result(timeout=30)
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=10)

        with self._lock:
            self._loop = None
            self._thread = None
            self._pid = None

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        pid = os.getpid()
        with self._lock:
            if (
                self._pid == pid
                and self._loop is not None
                and self._thread is not None
                and self._thread.is_alive()
            ):
                return self._loop

            loop = asyncio.new_event_loop()
            ready = threading.Event()

            def run_loop() -> None:
                asyncio.set_event_loop(loop)
                ready.set()
                loop.run_forever()
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                loop.close()

            thread = threading.Thread(
                target=run_loop,
                name="flashmarket-celery-asyncio",
                daemon=True,
            )
            thread.start()
            ready.wait(timeout=5)
            if not thread.is_alive():
                raise RuntimeError("Celery asyncio event loop failed to start")

            self._pid = pid
            self._loop = loop
            self._thread = thread
            return loop
