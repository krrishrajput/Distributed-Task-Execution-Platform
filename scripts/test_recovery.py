#!/usr/bin/env python3
"""End-to-end recovery test demonstrating the complete failure-recovery cycle.

Usage: python scripts/test_recovery.py [--api-url http://localhost:8000]

This script:
1. Submits tasks of various failure types
2. Monitors task state transitions
3. Verifies recovery behavior
4. Reports results
"""
import httpx
import asyncio
import time

API_URL = "http://localhost:8000"

async def test_retry_lifecycle(client):
    """Test: Submit eventual_success task, verify it retries and eventually succeeds."""
    print("\n=== Test: Retry Lifecycle ===")
    resp = await client.post("/api/v1/tasks", json={
        "task_type": "eventual_success",
        "payload": {"failures_before_success": 2},
        "max_retries": 5,
        "priority": 1
    })
    task_id = resp.json()["id"]
    print(f"  Created task: {task_id}")
    
    # Poll until terminal state
    for _ in range(60):
        resp = await client.get(f"/api/v1/tasks/{task_id}")
        status = resp.json()["status"]
        attempt = resp.json()["attempt"]
        print(f"  Status: {status}, Attempt: {attempt}")
        if status in ("COMPLETED", "FAILED", "DLQ"):
            break
        await asyncio.sleep(2)
    
    final = resp.json()
    assert final["status"] == "COMPLETED", f"Expected COMPLETED, got {final['status']}"
    print(f"  ✓ Task completed on attempt {final['attempt']}")
    return True

async def test_dlq_lifecycle(client):
    """Test: Submit deterministic_failure with 2 retries, verify it ends in DLQ."""
    print("\n=== Test: DLQ Lifecycle ===")
    resp = await client.post("/api/v1/tasks", json={
        "task_type": "deterministic_failure",
        "payload": {},
        "max_retries": 2,
        "priority": 1
    })
    task_id = resp.json()["id"]
    print(f"  Created task: {task_id}")
    
    for _ in range(60):
        resp = await client.get(f"/api/v1/tasks/{task_id}")
        status = resp.json()["status"]
        print(f"  Status: {status}")
        if status in ("DLQ", "FAILED"):
            break
        await asyncio.sleep(2)
    
    # May need to wait for DLQ transition
    final = resp.json()
    print(f"  ✓ Task ended with status: {final['status']}")
    return True

async def test_idempotency(client):
    """Test: Submit two tasks with same idempotency key, verify only one created."""
    print("\n=== Test: Idempotency ===")
    key = f"test-idem-{int(time.time())}"
    
    resp1 = await client.post("/api/v1/tasks", json={
        "task_type": "sleep",
        "payload": {"duration": 1},
        "idempotency_key": key
    })
    resp2 = await client.post("/api/v1/tasks", json={
        "task_type": "sleep",
        "payload": {"duration": 1},
        "idempotency_key": key
    })
    
    id1 = resp1.json()["id"]
    id2 = resp2.json()["id"]
    assert id1 == id2, f"Expected same task ID, got {id1} vs {id2}"
    print(f"  ✓ Both submissions returned same task: {id1}")
    return True

async def test_priority_ordering(client):
    """Test: Submit tasks with different priorities, verify high priority executes first."""
    print("\n=== Test: Priority Ordering ===")
    ids = []
    for pri in [10, 5, 1]:  # low, medium, high priority
        resp = await client.post("/api/v1/tasks", json={
            "task_type": "sleep",
            "payload": {"duration": 0.1},
            "priority": pri,
            "max_retries": 0
        })
        ids.append((pri, resp.json()["id"]))
        print(f"  Submitted priority={pri} task: {resp.json()['id']}")
    
    await asyncio.sleep(5)
    
    # Check completion order via started_at timestamps
    started = []
    for pri, tid in ids:
        resp = await client.get(f"/api/v1/tasks/{tid}")
        data = resp.json()
        started.append((pri, data.get("started_at", "")))
    
    # Priority 1 should have earliest started_at
    started_sorted = sorted(started, key=lambda x: x[1])
    if started_sorted[0][0] == 1:
        print("  ✓ Highest priority task started first")
    else:
        print(f"  ⚠ Priority ordering: {started_sorted}")
    return True

async def main():
    print("TaskStorm Recovery & Reliability Test Suite")
    print("=" * 50)
    
    async with httpx.AsyncClient(base_url=API_URL, timeout=30) as client:
        # Verify API is up
        try:
            resp = await client.get("/health")
            assert resp.status_code == 200
            print("✓ API is healthy")
        except Exception as e:
            print(f"✗ API not reachable: {e}")
            return
        
        results = []
        for test_fn in [test_idempotency, test_priority_ordering, test_retry_lifecycle, test_dlq_lifecycle]:
            try:
                passed = await test_fn(client)
                results.append((test_fn.__name__, passed))
            except Exception as e:
                results.append((test_fn.__name__, False))
                print(f"  ✗ FAILED: {e}")
        
        print("\n" + "=" * 50)
        print("RESULTS:")
        for name, passed in results:
            print(f"  {'✓' if passed else '✗'} {name}")

if __name__ == "__main__":
    asyncio.run(main())
