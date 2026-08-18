import pytest
from app.queue.task_queue import TaskQueue
from app.models.task import TaskCreate, Task

@pytest.mark.asyncio
async def test_stale_worker_completion_rejected(task_queue: TaskQueue, redis):
    task_in = TaskCreate(task_type="test", payload={})
    res = await task_queue.enqueue(task_in)
    task_id = res.id if isinstance(res, Task) else res
    
    task_a, lease_id_a = await task_queue.claim("worker_a")
    assert task_a.id == task_id
    
    # Simulate expiration by deleting lease and recovering
    await redis.delete(f"ts:lease:{task_id}")
    await redis.srem("ts:tasks:active", task_id)
    await redis.sadd("ts:worker:worker_a:tasks", task_id)
    # Recover task manually (simulate detector)
    await task_queue.scripts.recover_task(["ts:tasks:active", "ts:queue:priority"], [task_id, 9])
    
    task_b, lease_id_b = await task_queue.claim("worker_b")
    assert task_b.id == task_id
    assert lease_id_a != lease_id_b
    
    # Worker A tries to complete
    success_a = await task_queue.complete(task_id, "worker_a", lease_id_a, {"result": "A"})
    assert success_a is False
    
    # Worker B completes
    success_b = await task_queue.complete(task_id, "worker_b", lease_id_b, {"result": "B"})
    assert success_b is True
