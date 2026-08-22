from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.models.task import Task, TaskCreate, TaskSummary, TaskStatus
from app.core.redis import get_redis, get_redis_client
from app.core.config import Settings, config
from app.queue.task_queue import TaskQueue
from app.queue.state import TaskStateManager
from redis.asyncio import Redis

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

async def get_task_queue(redis: Redis = Depends(get_redis_client)) -> TaskQueue:
    return TaskQueue(redis, config)

async def get_state_manager(redis: Redis = Depends(get_redis_client)) -> TaskStateManager:
    return TaskStateManager(redis)

@router.post("", status_code=status.HTTP_201_CREATED, response_model=Task)
async def create_task(
    task_create: TaskCreate,
    queue: TaskQueue = Depends(get_task_queue)
):
    from app.models.task import TASK_TYPES
    if task_create.task_type not in TASK_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid task_type. Must be one of: {TASK_TYPES}")
        
    if len(str(task_create.payload).encode("utf-8")) > config.MAX_PAYLOAD_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Payload too large")
        
    result = await queue.enqueue(task_create)
    if isinstance(result, str):
        # existing task from idempotency key
        state = TaskStateManager(queue.redis)
        existing = await state.get_task(result)
        return existing
        
    return result

@router.get("")
async def list_tasks(
    status: Optional[TaskStatus] = None,
    limit: int = 50,
    offset: int = 0,
    state: TaskStateManager = Depends(get_state_manager)
):
    tasks = await state.list_tasks(status=status, limit=limit, offset=offset)
    total = await state.count_tasks(status=status)
    page = offset // limit + 1
    pages = max(1, (total + limit - 1) // limit)
    return {
        "items": tasks,
        "total": total,
        "page": page,
        "size": limit,
        "pages": pages
    }

@router.get("/dlq", response_model=List[TaskSummary])
async def list_dlq_tasks(
    limit: int = 50,
    offset: int = 0,
    state: TaskStateManager = Depends(get_state_manager)
):
    # Fetch from ts:dlq
    task_ids = await state.redis.lrange("ts:dlq", offset, offset + limit - 1)
    tasks = []
    for tid in task_ids:
        t = await state.get_task(tid)
        if t:
            tasks.append(TaskSummary(**t.model_dump()))
    return tasks

@router.get("/{task_id}", response_model=Task)
async def get_task(
    task_id: str,
    state: TaskStateManager = Depends(get_state_manager)
):
    task = await state.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.post("/{task_id}/cancel", response_model=Task)
async def cancel_task(
    task_id: str,
    state: TaskStateManager = Depends(get_state_manager)
):
    task = await state.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status not in {TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RETRYING, TaskStatus.RUNNING}:
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in {task.status} state")
        
    from datetime import datetime, timezone
    import json
    
    task.status = TaskStatus.CANCELLED
    task.updated_at = datetime.now(timezone.utc).isoformat()
    
    async with state.redis.pipeline(transaction=True) as pipe:
        pipe.hset(f"ts:task:{task_id}", "data", task.model_dump_json())
        pipe.zrem("ts:queue:priority", task_id)
        pipe.zrem("ts:queue:scheduled", task_id)
        pipe.zrem("ts:queue:retry", task_id)
        pipe.delete(f"ts:lease:{task_id}")
        
        event = {
            "event_type": "TASK_CANCELLED",
            "timestamp": task.updated_at,
            "task_id": task_id,
            "details": {}
        }
        pipe.publish("ts:events", json.dumps(event))
        
        await pipe.execute()
    
    return task

@router.post("/{task_id}/retry", response_model=Task)
async def retry_task(
    task_id: str,
    state: TaskStateManager = Depends(get_state_manager)
):
    task = await state.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status not in {TaskStatus.FAILED, TaskStatus.DLQ}:
        raise HTTPException(status_code=400, detail=f"Cannot retry task in {task.status} state")
        
    original_status = task.status
    task.status = TaskStatus.QUEUED
    task.attempt = 0
    await state.redis.hset(f"ts:task:{task_id}", "data", task.model_dump_json())
    
    if original_status == TaskStatus.DLQ:
        await state.redis.lrem("ts:dlq", 0, task_id)
        
    await state.redis.zadd("ts:queue:priority", {task_id: task.priority})
    
    return task
