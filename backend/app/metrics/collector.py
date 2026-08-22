from redis.asyncio import Redis
import json
import time
import statistics
from datetime import datetime

class MetricsCollector:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_metrics(self) -> dict:
        pipe = self.redis.pipeline()
        pipe.get("ts:metrics:submitted")
        pipe.get("ts:metrics:completed")
        pipe.get("ts:metrics:failed")
        pipe.zcard("ts:queue:priority")
        pipe.zcard("ts:queue:scheduled")
        pipe.zcard("ts:queue:retry")
        pipe.scard("ts:tasks:active")
        pipe.scard("ts:workers")
        pipe.llen("ts:dlq")
        
        results = await pipe.execute()
        
        submitted = int(results[0] or 0)
        completed = int(results[1] or 0)
        failed = int(results[2] or 0)
        q_prio = results[3]
        q_sched = results[4]
        q_retry = results[5]
        active_tasks = results[6]
        active_workers = results[7]
        dlq_depth = results[8]
        
        
        
        
        # Scan completed tasks for real metrics
        task_ids = await self.redis.smembers("ts:tasks:all")
        
        completed_tasks = []
        for tid in list(task_ids)[:500]: # limit to avoid blocking
            tid_str = tid.decode() if isinstance(tid, bytes) else tid
            raw = await self.redis.hget(f"ts:task:{tid_str}", "data")
            if raw:
                try:
                    data = json.loads(raw)
                    if data.get("status") == "COMPLETED":
                        completed_tasks.append(data)
                except Exception:
                    pass
        
        durations = [t.get("execution_duration_ms", 0) for t in completed_tasks if t.get("execution_duration_ms")]
        
        if durations:
            durations.sort()
            latency_p50 = float(statistics.median(durations))
            latency_p95 = float(statistics.quantiles(durations, n=100)[94] if len(durations) >= 2 else max(durations))
            latency_p99 = float(statistics.quantiles(durations, n=100)[98] if len(durations) >= 2 else max(durations))
            avg_duration = sum(durations) / len(durations)
        else:
            latency_p50 = 0.0
            latency_p95 = 0.0
            latency_p99 = 0.0
            avg_duration = 0.0
            
        # Calculate throughput (completions per minute based on time window)
        now = time.time()
        one_min_ago = now - 60
        recent_completions = 0
        for t in completed_tasks:
            completed_at_str = t.get("completed_at")
            if completed_at_str:
                try:
                    # Handle ISO format
                    completed_at = datetime.fromisoformat(completed_at_str.replace("Z", "+00:00")).timestamp()
                    if completed_at >= one_min_ago:
                        recent_completions += 1
                except Exception:
                    pass
                    
        throughput = recent_completions / 60.0

        
        worker_concurrency_total = 0
        for wid in await self.redis.smembers("ts:workers"):
            w_info = await self.redis.hget("ts:worker_info", wid)
            if w_info:
                try:
                    import json
                    w_dict = json.loads(w_info)
                    worker_concurrency_total += w_dict.get("concurrency", 10)
                except Exception:
                    worker_concurrency_total += 10
        
        worker_utilization = (active_tasks / max(worker_concurrency_total, 1)) * 100.0
        failure_rate = (failed / max(submitted, 1)) * 100.0
        
        retry_count = int(await self.redis.get("ts:metrics:retried") or 0)
        recovery_count = int(await self.redis.get("ts:metrics:recovered") or 0)
        retry_rate = (retry_count / max(submitted, 1)) * 100.0

        return {
            "throughput": float(throughput),
            "queue_depth": int(q_prio),
            "latency_p50": float(latency_p50),
            "latency_p95": float(latency_p95),
            "latency_p99": float(latency_p99),
            "avg_execution_duration": float(avg_duration),
            "retry_rate": float(retry_rate),
            "failure_rate": float(failure_rate),
            "worker_utilization": float(worker_utilization),
            "recovery_count": recovery_count,
            "dlq_count": int(dlq_depth),
            "scheduled_count": int(q_sched),
            "retry_queue_count": int(q_retry),
            "priority_breakdown": {}, # Need to compute this by scanning priority queue if small, or keep empty for now to avoid fake data
            "active_workers": int(active_workers),
            "submitted": int(submitted),
            "completed": int(completed),
            "failed": int(failed)
        }

