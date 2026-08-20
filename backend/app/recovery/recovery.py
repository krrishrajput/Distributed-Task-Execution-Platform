import asyncio
from datetime import datetime, timezone
from app.core.config import Settings
from app.queue.task_queue import TaskQueue
from app.recovery.detector import StaleWorkerDetector
from app.core.logging import get_logger

logger = get_logger(__name__)

class RecoveryService:
    def __init__(self, task_queue: TaskQueue, config: Settings):
        self.task_queue = task_queue
        self.config = config
        self.detector = StaleWorkerDetector(task_queue.redis, config)
        self.running = False
        self._task = None

    async def start(self):
        self.running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("Recovery service started")

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
        logger.info("Recovery service stopped")

    async def _loop(self):
        while self.running:
            try:
                offline_workers = await self.detector.scan_workers()
                if offline_workers:
                    await self._recover_abandoned_tasks(offline_workers)
            except Exception as e:
                logger.error(f"Error in recovery loop: {e}")
            await asyncio.sleep(self.config.RECOVERY_INTERVAL_SECONDS)

    async def _recover_abandoned_tasks(self, offline_workers: list[str]):
        # Check active tasks for expired leases or offline worker owners
        active_task_ids = await self.task_queue.redis.smembers(self.task_queue.active_tasks)
        now_str = datetime.now(timezone.utc).isoformat()
        
        for task_id in active_task_ids:
            lease_exists = await self.task_queue.redis.exists(f"ts:lease:{task_id}")
            should_recover = not lease_exists

            if lease_exists and offline_workers:
                # Inspect task data to see if owner worker is offline
                raw = await self.task_queue.redis.hget(f"ts:task:{task_id}", "data")
                if raw:
                    import json
                    tdata = json.loads(raw)
                    if tdata.get("worker_id") in offline_workers:
                        logger.info(f"Worker {tdata.get('worker_id')} is offline, invalidating lease for task {task_id}")
                        await self.task_queue.redis.delete(f"ts:lease:{task_id}")
                        should_recover = True

            if should_recover:
                logger.info(f"Attempting recovery for task {task_id}")
                await self._recover_task(task_id, now_str)

    async def _recover_task(self, task_id: str, now_str: str):
        keys = [
            f"ts:task:{task_id}",
            f"ts:lease:{task_id}",
            self.task_queue.priority_queue,
            self.task_queue.active_tasks,
            "ts:worker", # prefix for worker_tasks_key
            self.task_queue.events_channel
        ]
        args = [task_id, now_str]
        
        res = await self.task_queue.scripts.recover_task(keys, args)
        if str(res).startswith("error:"):
            logger.debug(f"Recovery failed for {task_id}: {res}")
        else:
            logger.info(f"Successfully recovered task {task_id}")
