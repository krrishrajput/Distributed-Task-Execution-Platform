import asyncio
from redis.asyncio import Redis
from datetime import datetime, timezone
from app.models.worker import WorkerInfo, WorkerStatus
from app.core.logging import get_logger

logger = get_logger(__name__)

class HeartbeatManager:
    def __init__(self, redis: Redis, worker_info: WorkerInfo, interval: float):
        self.redis = redis
        self.worker_info = worker_info
        self.interval = interval
        self._task = None

    async def start(self):
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Started heartbeat for worker {self.worker_info.id}")

    async def stop(self):
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        # Mark offline
        self.worker_info.status = WorkerStatus.OFFLINE
        await self._publish()

    async def _heartbeat_loop(self):
        try:
            while True:
                self.worker_info.last_heartbeat = datetime.now(timezone.utc)
                self.worker_info.uptime_seconds = (self.worker_info.last_heartbeat - self.worker_info.started_at).total_seconds()
                await self._publish()
                await asyncio.sleep(self.interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat loop error: {e}")

    async def _publish(self):
        key = f"ts:worker_info:{self.worker_info.id}"
        await self.redis.set(key, self.worker_info.model_dump_json(), ex=int(self.interval * 3))
        # Keep worker in set of all workers
        await self.redis.sadd("ts:workers", self.worker_info.id)
