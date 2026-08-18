from __future__ import annotations

from redis.asyncio import Redis
import json
from app.models.task import Task, TaskSummary, TaskStatus

class TaskStateManager:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_task(self, task_id: str) -> Task | None:
        raw_data = await self.redis.hget(f"ts:task:{task_id}", "data")
        if raw_data:
            return Task.model_validate_json(raw_data)
        return None

    async def get_queue_depth(self) -> int:
        return await self.redis.zcard("ts:queue:priority")

    async def get_active_count(self) -> int:
        return await self.redis.scard("ts:tasks:active")
