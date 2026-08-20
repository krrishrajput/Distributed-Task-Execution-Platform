from __future__ import annotations

from redis.asyncio import Redis
import json
from typing import Optional, List
from app.models.task import Task, TaskSummary, TaskStatus

class TaskStateManager:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_task(self, task_id: str) -> Task | None:
        raw_data = await self.redis.hget(f"ts:task:{task_id}", "data")
        if raw_data:
            return Task.model_validate_json(raw_data)
        return None

    async def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[TaskSummary]:
        task_ids = await self.redis.smembers("ts:tasks:all")
        summaries = []
        for tid in task_ids:
            task = await self.get_task(tid)
            if task:
                if status is None or task.status == status:
                    summaries.append(TaskSummary(
                        id=task.id,
                        task_type=task.task_type,
                        status=task.status,
                        priority=task.priority,
                        attempt=task.attempt,
                        worker_id=task.worker_id,
                        created_at=task.created_at,
                        execution_duration_ms=task.execution_duration_ms
                    ))
        
        # Sort by created_at descending
        summaries.sort(key=lambda t: t.created_at, reverse=True)
        return summaries[offset:offset + limit]

    async def get_queue_depth(self) -> int:
        return await self.redis.zcard("ts:queue:priority")

    async def get_active_count(self) -> int:
        return await self.redis.scard("ts:tasks:active")

    async def count_tasks(self, status: Optional[str] = None) -> int:
        task_ids = await self.redis.smembers("ts:tasks:all")
        if not status:
            return len(task_ids)
        count = 0
        for tid in task_ids:
            raw = await self.redis.hget(f"ts:task:{tid}", "data")
            if raw:
                import json
                data = json.loads(raw)
                if data.get("status") == str(status):
                    count += 1
        return count
