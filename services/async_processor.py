import asyncio
import logging
from typing import Callable, Coroutine, Any

logger = logging.getLogger(__name__)


class AsyncCDRProcessor:

    def __init__(self):
        self._handlers: list[Callable[..., Coroutine]] = []
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: asyncio.Task | None = None

    def register_handler(self, handler: Callable[..., Coroutine]):
        self._handlers.append(handler)

    async def enqueue(self, cdr: Any):
        await self._queue.put(cdr)

    async def _worker(self):
        while True:
            try:
                cdr = await self._queue.get()
                tasks = [handler(cdr) for handler in self._handlers]
                await asyncio.gather(*tasks, return_exceptions=True)
                self._queue.task_done()
            except Exception as e:
                logger.error(f"CDR processing error: {e}", exc_info=True)

    def start(self):
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())
            logger.info("Async CDR processor started")

    async def stop(self):
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
            logger.info("Async CDR processor stopped")
