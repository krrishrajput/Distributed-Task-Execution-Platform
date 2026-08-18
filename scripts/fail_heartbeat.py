#!/usr/bin/env python3
"""Simulate heartbeat loss by submitting long-running tasks and then checking worker status.

Usage: python scripts/fail_heartbeat.py [--api-url http://localhost:8000]
"""
import httpx
import asyncio
import argparse

API_URL = "http://localhost:8000"

async def check_workers(api_url: str):
    async with httpx.AsyncClient(base_url=api_url, timeout=30) as client:
        try:
            resp = await client.get("/api/v1/workers")
            if resp.status_code == 200:
                workers = resp.json()
                print("--- Worker Status ---")
                for w in workers:
                    print(f"Worker {w.get('id', 'N/A')} - Status: {w.get('status', 'UNKNOWN')} - Last Heartbeat: {w.get('last_heartbeat')}")
            else:
                print(f"Failed to fetch workers: {resp.status_code}")
        except Exception as e:
            print(f"Error fetching workers: {e}")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default=API_URL)
    args = parser.parse_args()
    
    print("Simulating heartbeat loss monitoring...")
    print("Checking initial worker status:")
    await check_workers(args.api_url)
    
    print("\nTo truly simulate heartbeat loss, manually stop a worker process")
    print("(e.g., kill -STOP <pid> or docker pause <container>)")
    print("and observe the status transition to UNHEALTHY or OFFLINE.")
    print("\nPolling worker status every 5 seconds (press Ctrl+C to exit)...")
    
    try:
        while True:
            await asyncio.sleep(5)
            await check_workers(args.api_url)
    except KeyboardInterrupt:
        print("\nExiting.")

if __name__ == "__main__":
    asyncio.run(main())
