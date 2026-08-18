import asyncio
from datetime import datetime, timezone
from app.queue.task_queue import TaskQueue
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class SchedulerService:
    def __init__(self, task_queue: TaskQueue, config: Settings):
        self.task_queue = task_queue
        self.config = config
        self.running = False
        self._tasks = []

    async def start(self):
        self.running = True
        self._tasks.append(asyncio.create_task(self._promote_scheduled_loop()))
        self._tasks.append(asyncio.create_task(self._promote_retries_loop()))
        self._tasks.append(asyncio.create_task(self._priority_aging_loop()))
        logger.info("Scheduler service started")

    async def stop(self):
        self.running = False
        for task in self._tasks:
            task.cancel()
        logger.info("Scheduler service stopped")

    async def _promote_scheduled_loop(self):
        while self.running:
            try:
                now = datetime.now(timezone.utc).timestamp()
                count = await self.task_queue.scripts.promote_scheduled(
                    [self.task_queue.scheduled_queue, self.task_queue.priority_queue],
                    [now, 100]
                )
                if count > 0:
                    logger.info(f"Promoted {count} scheduled tasks")
            except Exception as e:
                logger.error(f"Error in promote scheduled: {e}")
            await asyncio.sleep(self.config.SCHEDULER_INTERVAL_SECONDS)

    async def _promote_retries_loop(self):
        while self.running:
            try:
                now = datetime.now(timezone.utc).timestamp()
                count = await self.task_queue.scripts.promote_retries(
                    [self.task_queue.retry_queue, self.task_queue.priority_queue],
                    [now, 100]
                )
                if count > 0:
                    logger.info(f"Promoted {count} retries")
            except Exception as e:
                logger.error(f"Error in promote retries: {e}")
            await asyncio.sleep(self.config.SCHEDULER_INTERVAL_SECONDS)

    async def _priority_aging_loop(self):
        while self.running:
            try:
                # We could implement a Lua script for priority aging, 
                # but for simplicity, wait for Phase 3 enhancement if needed.
                pass
            except Exception as e:
                logger.error(f"Error in priority aging: {e}")
            await asyncio.sleep(self.config.PRIORITY_AGING_INTERVAL_SECONDS)
