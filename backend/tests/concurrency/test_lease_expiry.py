import pytest
import asyncio
from app.queue.task_queue import TaskQueue
from app.models.task import TaskCreate

@pytest.mark.asyncio
async def test_lease_expiry_and_recovery(task_queue: TaskQueue, redis, test_settings):
    original_duration = test_settings.TASK_LEASE_DURATION_SECONDS
    test_settings.TASK_LEASE_DURATION_SECONDS = 1
    
    task_in = TaskCreate(task_type="test", payload={})
    res = await task_queue.enqueue(task_in)
    
    task, lease_id = await task_queue.claim("w1")
    assert task is not None
    
    # Wait for lease to expire
    await asyncio.sleep(1.5)
    
    # Verify lease is gone
    lease_key = f"ts:lease:{task.id}"
    exists = await redis.exists(lease_key)
    assert exists == 0
    
    # Recovering task via recovery method
    recovered = await task_queue.recover(task.id)
    assert recovered is True
    
    # Claim again
    task2, lease_id2 = await task_queue.claim("w2")
    assert task2 is not None
    assert task2.id == task.id
    assert lease_id != lease_id2
    
    test_settings.TASK_LEASE_DURATION_SECONDS = original_duration
