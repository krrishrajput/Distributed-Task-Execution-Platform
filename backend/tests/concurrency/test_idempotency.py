import pytest
import asyncio
from uuid import uuid4
from app.queue.task_queue import TaskQueue
from app.models.task import TaskCreate, Task

@pytest.mark.asyncio
async def test_concurrent_idempotency(task_queue: TaskQueue):
    ikey = str(uuid4())
    task_in = TaskCreate(task_type="test", payload={}, idempotency_key=ikey)
    
    async def enqueue_worker():
        res = await task_queue.enqueue(task_in)
        return res.id if isinstance(res, Task) else res
        
    results = await asyncio.gather(*(enqueue_worker() for _ in range(20)))
    
    first_id = results[0]
    for r in results:
        assert r == first_id
        
    t1, l1 = await task_queue.claim("w")
    assert t1 is not None
    assert t1.id == first_id
    
    t2, l2 = await task_queue.claim("w")
    assert t2 is None
