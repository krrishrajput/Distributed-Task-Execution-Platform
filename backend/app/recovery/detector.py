import asyncio
from datetime import datetime, timezone
import json
from redis.asyncio import Redis
from app.core.config import Settings
from app.models.worker import WorkerInfo, WorkerStatus
from app.core.logging import get_logger

logger = get_logger(__name__)

class StaleWorkerDetector:
    def __init__(self, redis: Redis, config: Settings):
        self.redis = redis
        self.config = config

    async def scan_workers(self) -> list[str]:
        offline_workers = []
        worker_ids = await self.redis.smembers("ts:workers")
        now = datetime.now(timezone.utc)
        
        for wid in worker_ids:
            key = f"ts:worker_info:{wid}"
            data = await self.redis.get(key)
            if not data:
                offline_workers.append(wid)
                await self.redis.srem("ts:workers", wid)
                logger.info(f"Worker {wid} info not found, marked offline")
                continue
                
            info = WorkerInfo.model_validate_json(data)
            time_since_heartbeat = (now - info.last_heartbeat).total_seconds()
            
            if time_since_heartbeat > self.config.HEARTBEAT_OFFLINE_THRESHOLD:
                info.status = WorkerStatus.OFFLINE
                await self.redis.set(key, info.model_dump_json())
                offline_workers.append(wid)
                await self.redis.srem("ts:workers", wid)
                logger.warning(f"Worker {wid} offline (no heartbeat for {time_since_heartbeat}s)")
            elif time_since_heartbeat > self.config.HEARTBEAT_UNHEALTHY_THRESHOLD:
                info.status = WorkerStatus.UNHEALTHY
                await self.redis.set(key, info.model_dump_json())
                
        return offline_workers
