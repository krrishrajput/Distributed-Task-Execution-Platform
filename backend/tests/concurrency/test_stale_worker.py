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
    
    # Simulate expiration by deleting lease
    await redis.delete(f"ts:lease:{task_id}")
    
    # Recover task via recovery logic
    recovered = await task_queue.recover(task_id)
    assert recovered is True
    
    task_b, lease_id_b = await task_queue.claim("worker_b")
    assert task_b.id == task_id
    assert lease_id_a != lease_id_b
    
    # Worker A tries to complete with stale lease_id_a -> REJECTED
    success_a = await task_queue.complete(task_id, "worker_a", lease_id_a, {"result": "A"})
    assert success_a is False
    
    # Worker B completes with valid lease_id_b -> SUCCESS
    success_b = await task_queue.complete(task_id, "worker_b", lease_id_b, {"result": "B"})
    assert success_b is True
