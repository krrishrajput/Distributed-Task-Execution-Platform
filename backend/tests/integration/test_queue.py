import pytest
import json
from app.queue.task_queue import TaskQueue
from app.models.task import TaskCreate, TaskStatus, Task
from datetime import datetime, timezone, timedelta
from uuid import uuid4

@pytest.mark.asyncio
async def test_enqueue_and_claim(task_queue: TaskQueue):
    task_in = TaskCreate(task_type="test", payload={"foo": "bar"})
    task_res = await task_queue.enqueue(task_in)
    
    assert isinstance(task_res, Task)
    task_id = task_res.id
    
    task, lease_id = await task_queue.claim("worker-1")
    assert task is not None
    assert task.id == task_id
    assert task.status == TaskStatus.RUNNING
    assert lease_id is not None

@pytest.mark.asyncio
async def test_enqueue_with_priority(task_queue: TaskQueue):
    task_low = TaskCreate(task_type="test", payload={}, priority=9)
    task_high = TaskCreate(task_type="test", payload={}, priority=1)
    
    t_low = await task_queue.enqueue(task_low)
    t_high = await task_queue.enqueue(task_high)
    
    t1, l1 = await task_queue.claim("worker-1")
    t2, l2 = await task_queue.claim("worker-1")
    
    assert t1.id == t_high.id
    assert t2.id == t_low.id

@pytest.mark.asyncio
async def test_claim_empty_queue(task_queue: TaskQueue):
    result = await task_queue.claim("worker-1")
    assert result == (None, None)

@pytest.mark.asyncio
async def test_complete_task(task_queue: TaskQueue, redis):
    task_in = TaskCreate(task_type="test", payload={})
    t_res = await task_queue.enqueue(task_in)
    task, lease_id = await task_queue.claim("w1")
    
    success = await task_queue.complete(task.id, "w1", lease_id, {"status": "ok"})
    assert success is True
    
    raw = await redis.hget(f"ts:task:{task.id}", "data")
    assert raw is not None
    t_after = Task.model_validate_json(raw)
    assert t_after.status == TaskStatus.COMPLETED
    assert t_after.result == {"status": "ok"}

@pytest.mark.asyncio
async def test_fail_task_with_retries(task_queue: TaskQueue, redis):
    task_in = TaskCreate(task_type="test", payload={}, max_retries=2)
    t_res = await task_queue.enqueue(task_in)
    task, lease_id = await task_queue.claim("w1")
    
    success = await task_queue.fail(task.id, "w1", lease_id, "error msg", 1)
    assert success is True
    
    raw = await redis.hget(f"ts:task:{task.id}", "data")
    assert raw is not None
    t_after = Task.model_validate_json(raw)
    assert t_after.status == TaskStatus.RETRYING

@pytest.mark.asyncio
async def test_fail_task_no_retries(task_queue: TaskQueue, redis):
    task_in = TaskCreate(task_type="test", payload={}, max_retries=0)
    t_res = await task_queue.enqueue(task_in)
    task, lease_id = await task_queue.claim("w1")
    
    await task_queue.fail(task.id, "w1", lease_id, "fatal", 1)
    
    raw = await redis.hget(f"ts:task:{task.id}", "data")
    assert raw is not None
    t_after = Task.model_validate_json(raw)
    assert t_after.status in (TaskStatus.FAILED, TaskStatus.DLQ)

@pytest.mark.asyncio
async def test_lease_creation(task_queue: TaskQueue, redis):
    task_in = TaskCreate(task_type="test", payload={})
    t_res = await task_queue.enqueue(task_in)
    task, lease_id = await task_queue.claim("w1")
    
    lease_key = f"ts:lease:{task.id}"
    exists = await redis.exists(lease_key)
    assert exists == 1

@pytest.mark.asyncio
async def test_lease_renewal(task_queue: TaskQueue, redis):
    task_in = TaskCreate(task_type="test", payload={})
    t_res = await task_queue.enqueue(task_in)
    task, lease_id = await task_queue.claim("w1")
    
    lease_key = f"ts:lease:{task.id}"
    
    success = await task_queue.renew_lease(task.id, "w1", lease_id)
    assert success is True

@pytest.mark.asyncio
async def test_idempotent_enqueue(task_queue: TaskQueue):
    ikey = str(uuid4())
    task1 = TaskCreate(task_type="test", payload={}, idempotency_key=ikey)
    task2 = TaskCreate(task_type="test", payload={}, idempotency_key=ikey)
    
    res1 = await task_queue.enqueue(task1)
    res2 = await task_queue.enqueue(task2)
    
    id1 = res1.id if isinstance(res1, Task) else res1
    id2 = res2.id if isinstance(res2, Task) else res2
    assert id1 == id2
    
    t, l = await task_queue.claim("w1")
    assert t.id == id1
    t_none, _ = await task_queue.claim("w1")
    assert t_none is None

@pytest.mark.asyncio
async def test_scheduled_task(task_queue: TaskQueue, redis):
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    task_in = TaskCreate(task_type="test", payload={}, scheduled_at=future_time)
    t_res = await task_queue.enqueue(task_in)
    
    t, l = await task_queue.claim("w1")
    assert t is None
    
    raw = await redis.hget(f"ts:task:{t_res.id}", "data")
    assert raw is not None
    t_obj = Task.model_validate_json(raw)
    assert t_obj.status == TaskStatus.PENDING
