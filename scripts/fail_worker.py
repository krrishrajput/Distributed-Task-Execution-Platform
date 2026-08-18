#!/usr/bin/env python3
"""Simulate worker failure by submitting tasks that expose failure recovery.

Usage: python scripts/fail_worker.py [--api-url http://localhost:8000] [--count 5]
"""
import httpx
import asyncio
import argparse
import sys
import time

API_URL = "http://localhost:8000"

async def submit_lease_expiration_tasks(api_url: str, count: int):
    """Submit tasks that take longer than lease duration, triggering lease expiry recovery."""
    async with httpx.AsyncClient(base_url=api_url, timeout=30) as client:
        for i in range(count):
            resp = await client.post("/api/v1/tasks", json={
                "task_type": "lease_expiration",
                "payload": {"duration": 120},  # longer than default 60s lease
                "priority": 5,
                "max_retries": 2
            })
            print(f"Submitted lease_expiration task {i+1}/{count}: {resp.json()['id']}")
    print("\nMonitor recovery via: GET /api/v1/events")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=API_URL)
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    await submit_lease_expiration_tasks(args.api_url, args.count)

if __name__ == "__main__":
    asyncio.run(main())
