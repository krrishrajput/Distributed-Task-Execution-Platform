import pytest
import asyncio
from app.queue.task_queue import TaskQueue
from app.models.task import TaskCreate

@pytest.mark.asyncio
async def test_concurrent_claim_single_task(task_queue: TaskQueue):
    task_in = TaskCreate(task_type="test", payload={})
    await task_queue.enqueue(task_in)
    
    async def claim_worker(worker_id):
        return await task_queue.claim(worker_id)
        
    results = await asyncio.gather(*(claim_worker(f"w-{i}") for i in range(10)))
    
    successes = [r for r in results if r[0] is not None]
    failures = [r for r in results if r[0] is None]
    
    assert len(successes) == 1
    assert len(failures) == 9

@pytest.mark.asyncio
async def test_concurrent_claim_multiple_tasks(task_queue: TaskQueue):
    for _ in range(5):
        await task_queue.enqueue(TaskCreate(task_type="test", payload={}))
        
    async def claim_worker(worker_id):
        return await task_queue.claim(worker_id)
        
    results = await asyncio.gather(*(claim_worker(f"w-{i}") for i in range(10)))
    
    successes = [r for r in results if r[0] is not None]
    failures = [r for r in results if r[0] is None]
    
    assert len(successes) == 5
    assert len(failures) == 5
    
    task_ids = set(r[0].id for r in successes)
    assert len(task_ids) == 5
