#!/usr/bin/env python3
"""TaskStorm benchmark suite.

Measures throughput, latency, and scaling characteristics.

Usage: python scripts/benchmark.py [--api-url http://localhost:8000] [--tasks 200]
"""
import httpx
import asyncio
import time
import statistics

async def run_benchmark(api_url, num_tasks, concurrency=20):
    """Submit tasks and measure completion metrics."""
    task_ids = []
    submit_start = time.monotonic()
    sem = asyncio.Semaphore(concurrency)
    
    async def submit(session, i):
        async with sem:
            resp = await session.post("/api/v1/tasks", json={
                "task_type": "sleep",
                "payload": {"duration": 0.1},
                "priority": 5,
                "max_retries": 0
            })
            return resp.json()["id"]
    
    async with httpx.AsyncClient(base_url=api_url, timeout=60) as client:
        tasks = [submit(client, i) for i in range(num_tasks)]
        task_ids = await asyncio.gather(*tasks)
    
    submit_elapsed = time.monotonic() - submit_start
    print(f"  Submitted {num_tasks} tasks in {submit_elapsed:.2f}s ({num_tasks/submit_elapsed:.1f}/s)")
    
    # Wait for completion
    all_start = time.monotonic()
    completed = 0
    durations = []
    
    async with httpx.AsyncClient(base_url=api_url, timeout=60) as client:
        while completed < num_tasks and (time.monotonic() - all_start) < 120:
            completed = 0
            for tid in task_ids:
                resp = await client.get(f"/api/v1/tasks/{tid}")
                data = resp.json()
                if data["status"] in ("COMPLETED", "FAILED"):
                    completed += 1
                    if data.get("execution_duration_ms"):
                        durations.append(data["execution_duration_ms"])
            
            if completed < num_tasks:
                await asyncio.sleep(1)
    
    total_elapsed = time.monotonic() - all_start
    
    if durations:
        durations.sort()
        p50 = durations[len(durations) // 2]
        p95 = durations[int(len(durations) * 0.95)]
        p99 = durations[int(len(durations) * 0.99)]
    else:
        p50 = p95 = p99 = 0
    
    print(f"  Completed: {completed}/{num_tasks}")
    print(f"  Total time: {total_elapsed:.2f}s")
    print(f"  Throughput: {completed/total_elapsed:.1f} tasks/sec")
    print(f"  Latency p50: {p50:.1f}ms  p95: {p95:.1f}ms  p99: {p99:.1f}ms")
    return {
        "tasks": num_tasks,
        "completed": completed,
        "submit_time": submit_elapsed,
        "total_time": total_elapsed,
        "throughput": completed/total_elapsed,
        "p50": p50, "p95": p95, "p99": p99
    }

async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--tasks", type=int, default=200)
    args = parser.parse_args()
    
    print("TaskStorm Benchmark")
    print("=" * 50)
    result = await run_benchmark(args.api_url, args.tasks)

if __name__ == "__main__":
    asyncio.run(main())
