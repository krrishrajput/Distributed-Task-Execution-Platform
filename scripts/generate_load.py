#!/usr/bin/env python3
"""Generate configurable task load for benchmarking TaskStorm.

Usage:
  python scripts/generate_load.py --count 100 --task-type sleep --concurrency 10
  python scripts/generate_load.py --count 500 --task-type random_failure --priority 1
  python scripts/generate_load.py --count 1000 --mix  # mixed task types
"""
import httpx
import asyncio
import argparse
import time
import random

API_URL = "http://localhost:8000"

TASK_CONFIGS = {
    "sleep": {"payload": {"duration": 0.5}, "max_retries": 0},
    "cpu_simulation": {"payload": {"iterations": 100000}, "max_retries": 0},
    "random_failure": {"payload": {"failure_rate": 0.3}, "max_retries": 3},
    "eventual_success": {"payload": {"failures_before_success": 2}, "max_retries": 5},
}

async def submit_tasks(api_url, count, task_type, priority, concurrency, mix):
    sem = asyncio.Semaphore(concurrency)
    submitted = 0
    errors = 0
    start_time = time.monotonic()
    
    async def submit_one(session, idx):
        nonlocal submitted, errors
        async with sem:
            tt = random.choice(list(TASK_CONFIGS.keys())) if mix else task_type
            cfg = TASK_CONFIGS[tt]
            try:
                resp = await session.post("/api/v1/tasks", json={
                    "task_type": tt,
                    "payload": cfg["payload"],
                    "priority": priority or random.randint(1, 10),
                    "max_retries": cfg["max_retries"]
                })
                if resp.status_code in (200, 201):
                    submitted += 1
                else:
                    errors += 1
            except Exception:
                errors += 1
    
    async with httpx.AsyncClient(base_url=api_url, timeout=30) as client:
        tasks = [submit_one(client, i) for i in range(count)]
        await asyncio.gather(*tasks)
    
    elapsed = time.monotonic() - start_time
    print(f"\n=== Load Generation Complete ===")
    print(f"Submitted: {submitted}")
    print(f"Errors: {errors}")
    print(f"Duration: {elapsed:.2f}s")
    print(f"Throughput: {submitted/elapsed:.1f} tasks/sec")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=API_URL)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--task-type", default="sleep", choices=list(TASK_CONFIGS.keys()))
    parser.add_argument("--priority", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--mix", action="store_true")
    args = parser.parse_args()
    await submit_tasks(args.api_url, args.count, args.task_type, args.priority, args.concurrency, args.mix)

if __name__ == "__main__":
    asyncio.run(main())
