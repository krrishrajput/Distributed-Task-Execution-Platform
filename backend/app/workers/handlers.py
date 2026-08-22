import asyncio
from concurrent.futures import ThreadPoolExecutor

# Bounded executor to prevent thread explosion
WORKER_POOL = ThreadPoolExecutor(max_workers=10)
import random
import time
from typing import Callable, Any

class TaskExecutionError(Exception):
    pass

HANDLER_REGISTRY: dict[str, Callable] = {}

def register_handler(task_type: str):
    def decorator(func: Callable):
        HANDLER_REGISTRY[task_type] = func
        return func
    return decorator

@register_handler("sleep")
async def handle_sleep(payload: dict, attempt: int) -> dict:
    duration = payload.get("duration", 1.0)
    await asyncio.sleep(min(duration, 300))
    return {"slept_for": duration}

def cpu_work(iterations: int):
    val = 0
    for _ in range(iterations):
        val += 1
    return val

@register_handler("cpu_simulation")
async def handle_cpu_simulation(payload: dict, attempt: int) -> dict:
    iterations = payload.get("iterations", 1_000_000)
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(WORKER_POOL, cpu_work, iterations)
    return {"result": result, "iterations": iterations}

@register_handler("random_failure")
async def handle_random_failure(payload: dict, attempt: int) -> dict:
    failure_rate = payload.get("failure_rate", 0.5)
    if random.random() < failure_rate:
        raise TaskExecutionError("Random failure triggered")
    return {"success": True}

@register_handler("deterministic_failure")
async def handle_deterministic_failure(payload: dict, attempt: int) -> dict:
    raise TaskExecutionError("Deterministic failure - always fails")

@register_handler("lease_expiration")
async def handle_lease_expiration(payload: dict, attempt: int) -> dict:
    duration = payload.get("duration", 120)
    await asyncio.sleep(duration)
    return {"completed_after": duration}

@register_handler("eventual_success")
async def handle_eventual_success(payload: dict, attempt: int) -> dict:
    failures_before_success = payload.get("failures_before_success", 3)
    if attempt <= failures_before_success:
        raise TaskExecutionError(f"Planned failure on attempt {attempt}")
    return {"succeeded_on_attempt": attempt}

@register_handler("test")
async def handle_test(payload: dict, attempt: int) -> dict:
    return {"status": "ok", "payload": payload}
