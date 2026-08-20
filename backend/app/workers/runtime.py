import asyncio
import os
import uuid
from datetime import datetime, timezone
from app.core.config import Settings
from app.queue.task_queue import TaskQueue
from app.models.worker import WorkerInfo, WorkerStatus
from app.workers.heartbeat import HeartbeatManager
from app.workers.lease import LeaseManager
from app.workers.handlers import HANDLER_REGISTRY
from app.core.logging import get_logger
from redis.asyncio import Redis

logger = get_logger(__name__)

class WorkerRuntime:
    def __init__(self, config: Settings, redis: Redis, task_queue: TaskQueue):
        self.config = config
        self.redis = redis
        self.task_queue = task_queue
        self.worker_id = f"worker-{uuid.uuid4().hex[:8]}"
        self.semaphore = asyncio.Semaphore(config.WORKER_CONCURRENCY)
        self.running = False
        self.active_tasks = set()
        
        self.worker_info = WorkerInfo(
            worker_id=self.worker_id,
            status=WorkerStatus.HEALTHY,
            last_heartbeat=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            active_tasks=0,
            completed_tasks=0,
            failed_tasks=0,
            hostname=os.uname().nodename,
            pid=os.getpid(),
            concurrency=config.WORKER_CONCURRENCY,
            uptime_seconds=0.0
        )
        
        self.heartbeat = HeartbeatManager(redis, self.worker_info, config.HEARTBEAT_INTERVAL_SECONDS)
        self.lease_manager = LeaseManager(task_queue, config.TASK_LEASE_DURATION_SECONDS / 2.0)
        self._loop_task = None

    async def start(self):
        self.running = True
        await self.heartbeat.start()
        logger.info(f"Worker {self.worker_id} started. Concurrency: {self.config.WORKER_CONCURRENCY}")
        self._loop_task = asyncio.create_task(self._claim_loop())

    async def _claim_loop(self):
        while self.running:
            await self.semaphore.acquire()
            try:
                task, lease_id = await self.task_queue.claim(self.worker_id)
                if task:
                    self.active_tasks.add(task.id)
                    self.worker_info.active_tasks = len(self.active_tasks)
                    asyncio.create_task(self._execute_task(task, lease_id))
                else:
                    self.semaphore.release()
                    await asyncio.sleep(1.0)
            except Exception as e:
                self.semaphore.release()
                logger.error(f"Error in claim loop: {e}")
                await asyncio.sleep(1.0)

    async def _execute_task(self, task, lease_id):
        try:
            handler = HANDLER_REGISTRY.get(task.task_type)
            if not handler:
                raise ValueError(f"No handler found for task type: {task.task_type}")

            self.lease_manager.start_renewal(task.id, self.worker_id, lease_id)
            logger.info(f"Executing task {task.id} (type: {task.task_type})")
            
            result = await handler(task.payload, task.attempt)
            
            success = await self.task_queue.complete(task.id, self.worker_id, lease_id, result)
            if success:
                self.worker_info.completed_tasks += 1
                logger.info(f"Task {task.id} completed successfully")
            else:
                logger.warning(f"Task {task.id} completion rejected by Redis (lease mismatch or stale worker)")
            
        except Exception as e:
            logger.warning(f"Task {task.id} failed: {e}")
            await self.task_queue.fail(task.id, self.worker_id, lease_id, str(e), task.attempt)
            self.worker_info.failed_tasks += 1
        finally:
            self.lease_manager.stop_renewal(task.id)
            self.active_tasks.remove(task.id)
            self.worker_info.active_tasks = len(self.active_tasks)
            self.semaphore.release()

    async def shutdown(self):
        logger.info("Worker shutting down gracefully...")
        self.running = False
        if self._loop_task:
            self._loop_task.cancel()
        
        # Wait for active tasks to finish or just drop them
        while self.active_tasks:
            logger.info(f"Waiting for {len(self.active_tasks)} active tasks to complete...")
            await asyncio.sleep(1)
            
        await self.heartbeat.stop()
        logger.info("Worker shutdown complete.")
