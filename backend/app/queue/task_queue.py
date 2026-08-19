from __future__ import annotations

from redis.asyncio import Redis
import json
import uuid
from datetime import datetime, timezone
from app.core.config import Settings
from app.models.task import Task, TaskCreate, TaskStatus
from app.queue.lua_scripts import LuaScriptManager
from app.queue.retry import calculate_retry_delay

class TaskQueue:
    def __init__(self, redis: Redis, config: Settings):
        self.redis = redis
        self.config = config
        self.scripts = LuaScriptManager(redis)
        self.priority_queue = "ts:queue:priority"
        self.scheduled_queue = "ts:queue:scheduled"
        self.retry_queue = "ts:queue:retry"
        self.active_tasks = "ts:tasks:active"
        self.dlq = "ts:dlq"
        self.events_channel = "ts:events"

    async def enqueue(self, task_create: TaskCreate, task_id: str = None) -> Task | str:
        if not task_id:
            task_id = str(uuid.uuid4())
        
        now = datetime.now(timezone.utc)
        task = Task(
            id=task_id,
            task_type=task_create.task_type,
            payload=task_create.payload,
            priority=task_create.priority,
            status=TaskStatus.QUEUED if not task_create.scheduled_at else TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            scheduled_at=task_create.scheduled_at,
            attempt=0,
            max_retries=task_create.max_retries,
            idempotency_key=task_create.idempotency_key,
            state_history=[],
            retry_history=[]
        )

        task_hash_key = f"ts:task:{task_id}"
        idempotency_key_key = f"ts:idempotency:{task_create.idempotency_key}" if task_create.idempotency_key else ""
        
        scheduled_at_score = task_create.scheduled_at.timestamp() if task_create.scheduled_at else 0
        # Score encoding: priority * 1e12 + timestamp_ns for FIFO ordering within same priority
        ns = int(now.timestamp() * 1e9) % 1000000000
        score = task_create.priority * 1000000000000 + ns

        keys = [
            task_hash_key, self.priority_queue, self.scheduled_queue,
            idempotency_key_key, "ts:metrics:submitted", self.events_channel, "ts:tasks:all"
        ]
        event_json = json.dumps({
            "type": "TASK_ENQUEUED",
            "task_id": task_id,
            "timestamp": now.isoformat() + "Z"
        })
        args = [
            task_id, task.model_dump_json(), score, scheduled_at_score,
            task_create.idempotency_key or "", event_json, self.config.IDEMPOTENCY_KEY_TTL_SECONDS
        ]

        result = await self.scripts.enqueue_task(keys, args)
        if len(result) > 1 and (result[1] == "duplicate" or result[1] == b"duplicate"):
            dup_id = result[0].decode("utf-8") if isinstance(result[0], bytes) else result[0]
            return dup_id
        
        return task

    async def claim(self, worker_id: str) -> tuple[Task | None, str | None]:
        lease_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        keys = [self.priority_queue, self.active_tasks, f"ts:worker:{worker_id}:tasks", self.events_channel]
        args = [worker_id, lease_id, self.config.TASK_LEASE_DURATION_SECONDS, int(now.timestamp()), now.isoformat()]
        
        raw_task = await self.scripts.claim_task(keys, args)
        if raw_task:
            task = Task.model_validate_json(raw_task)
            return task, lease_id
        return None, None

    async def complete(self, task_id: str, worker_id: str, lease_id: str, result: any = None) -> bool:
        now = datetime.now(timezone.utc)
        timestamp_ms = int(now.timestamp() * 1000)
        keys = [f"ts:task:{task_id}", f"ts:lease:{task_id}", self.active_tasks, f"ts:worker:{worker_id}:tasks", "ts:metrics:completed", self.events_channel]
        args = [task_id, worker_id, lease_id, json.dumps(result) if result else "", now.isoformat(), timestamp_ms]
        
        res = await self.scripts.complete_task(keys, args)
        return res == b"ok" or res == "ok"

    async def fail(self, task_id: str, worker_id: str, lease_id: str, error: str, attempt: int) -> bool:
        now = datetime.now(timezone.utc)
        timestamp_ms = int(now.timestamp() * 1000)
        delay = calculate_retry_delay(attempt, self.config.TASK_RETRY_BASE_DELAY, self.config.TASK_RETRY_MAX_DELAY)
        retry_score = now.timestamp() + delay
        
        keys = [f"ts:task:{task_id}", f"ts:lease:{task_id}", self.active_tasks, f"ts:worker:{worker_id}:tasks", self.retry_queue, self.dlq, "ts:metrics:failed", self.events_channel]
        args = [task_id, worker_id, lease_id, error, now.isoformat(), retry_score, timestamp_ms]
        
        res = await self.scripts.fail_task(keys, args)
        return not str(res).startswith("error:")

    async def renew_lease(self, task_id: str, worker_id: str, lease_id: str) -> bool:
        res = await self.scripts.renew_lease([f"ts:lease:{task_id}"], [lease_id, self.config.TASK_LEASE_DURATION_SECONDS])
        return res == b"ok" or res == "ok"

    async def recover(self, task_id: str) -> bool:
        now_str = datetime.now(timezone.utc).isoformat()
        keys = [
            f"ts:task:{task_id}",
            f"ts:lease:{task_id}",
            self.priority_queue,
            self.active_tasks,
            "ts:worker",
            self.events_channel
        ]
        args = [task_id, now_str]
        res = await self.scripts.recover_task(keys, args)
        return res in ("ok", b"ok")
