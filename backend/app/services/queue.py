import asyncio
from typing import Optional, Callable, Awaitable
from datetime import datetime
import aiosqlite
from ..database import DATABASE_PATH, get_db
from ..models.task import TaskStatus
import logging

logger = logging.getLogger(__name__)


class TaskQueue:
    def __init__(self):
        self._running = False
        self._workers: list[asyncio.Task] = []
        self._task_handler: Optional[Callable[[int], Awaitable[None]]] = None
        self._max_concurrent = 2
        self._progress_callbacks: dict[int, Callable[[int, int], Awaitable[None]]] = {}

    def set_task_handler(self, handler: Callable[[int], Awaitable[None]]):
        """Set the handler function for processing tasks."""
        self._task_handler = handler

    def set_max_concurrent(self, max_concurrent: int):
        """Set maximum concurrent tasks."""
        self._max_concurrent = max_concurrent
        if self._running:
            self._reap_done_workers()
            for i in range(len(self._workers), self._max_concurrent):
                worker = asyncio.create_task(self._worker(i))
                self._workers.append(worker)

    async def start(self):
        """Start the task queue workers."""
        if self._running:
            return

        self._running = True
        self._reap_done_workers()
        for i in range(self._max_concurrent):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
        logger.info(f"Task queue started with {self._max_concurrent} workers")

    async def stop(self):
        """Stop the task queue workers."""
        self._running = False
        for worker in self._workers:
            worker.cancel()
        self._workers.clear()
        logger.info("Task queue stopped")

    async def _worker(self, worker_id: int):
        """Worker coroutine that processes tasks from the queue."""
        logger.info(f"Worker {worker_id} started")

        while self._running:
            if worker_id >= self._max_concurrent:
                break
            try:
                task_id = await self._claim_next_task()

                if task_id is None:
                    await asyncio.sleep(1)
                    continue

                logger.info(f"Worker {worker_id} processing task {task_id}")

                try:
                    if self._task_handler:
                        await self._task_handler(task_id)

                    status = await self._get_task_status(task_id)
                    if status == TaskStatus.CANCELLED.value:
                        logger.info(f"Task {task_id} cancelled, skipping completion")
                    else:
                        await self._update_task_status(
                            task_id, TaskStatus.COMPLETED, progress=100
                        )
                        logger.info(f"Task {task_id} completed")

                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    status = await self._get_task_status(task_id)
                    if status != TaskStatus.CANCELLED.value:
                        await self._update_task_status(
                            task_id, TaskStatus.FAILED, error_message=str(e)
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)

        logger.info(f"Worker {worker_id} stopped")

    def _reap_done_workers(self):
        """Remove completed worker tasks from the list."""
        self._workers = [worker for worker in self._workers if not worker.done()]

    async def _claim_next_task(self) -> Optional[int]:
        """Atomically claim the next pending task and mark it as processing."""
        async with get_db() as db:
            cursor = await db.execute(
                """
                UPDATE tasks
                SET status = ?, updated_at = ?
                WHERE id = (
                    SELECT id FROM tasks
                    WHERE status = ?
                    ORDER BY created_at ASC
                    LIMIT 1
                )
                RETURNING id
                """,
                (
                    TaskStatus.PROCESSING.value,
                    datetime.now().isoformat(),
                    TaskStatus.PENDING.value,
                ),
            )
            row = await cursor.fetchone()
            await db.commit()
            return row["id"] if row else None

    async def _get_task_status(self, task_id: int) -> Optional[str]:
        """Fetch current task status from the database."""
        async with get_db() as db:
            cursor = await db.execute(
                "SELECT status FROM tasks WHERE id = ?",
                (task_id,),
            )
            row = await cursor.fetchone()
            return row["status"] if row else None

    async def _update_task_status(
        self,
        task_id: int,
        status: TaskStatus,
        progress: Optional[int] = None,
        error_message: Optional[str] = None,
    ):
        """Update task status in the database."""
        async with get_db() as db:
            updates = ["status = ?", "updated_at = ?"]
            params = [status.value, datetime.now().isoformat()]

            if progress is not None:
                updates.append("progress = ?")
                params.append(progress)

            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            if status == TaskStatus.COMPLETED:
                updates.append("completed_at = ?")
                params.append(datetime.now().isoformat())

            params.append(task_id)

            await db.execute(
                f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            await db.commit()

    async def update_progress(self, task_id: int, progress: int):
        """Update task progress."""
        async with get_db() as db:
            await db.execute(
                "UPDATE tasks SET progress = ?, updated_at = ? WHERE id = ?",
                (progress, datetime.now().isoformat(), task_id),
            )
            await db.commit()

        # Call progress callback if registered
        if task_id in self._progress_callbacks:
            await self._progress_callbacks[task_id](task_id, progress)

    def register_progress_callback(
        self, task_id: int, callback: Callable[[int, int], Awaitable[None]]
    ):
        """Register a callback for progress updates."""
        self._progress_callbacks[task_id] = callback

    def unregister_progress_callback(self, task_id: int):
        """Unregister a progress callback."""
        self._progress_callbacks.pop(task_id, None)


# Global queue instance
task_queue = TaskQueue()
