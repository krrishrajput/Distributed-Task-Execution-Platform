from redis.asyncio import Redis

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
        
        failure_rate = (failed / max(submitted, 1)) * 100.0
        worker_utilization = (active_tasks / max(active_workers * 10, 1)) * 100.0
        
        # Basic throughput approximation (since we don't have time windows yet)
        throughput = completed / 60.0 if completed > 0 else 0.0

        return {
            "throughput": throughput,
            "queue_depth": q_prio,
            "latency_p50": 12.5,  # Mocked until we track execution duration
            "latency_p95": 45.2,
            "latency_p99": 120.0,
            "avg_execution_duration": 15.0,
            "retry_rate": failure_rate * 0.8, # Approximation
            "failure_rate": failure_rate,
            "worker_utilization": worker_utilization,
            "recovery_count": 0,
            "dlq_count": dlq_depth,
            "scheduled_count": q_sched,
            "retry_queue_count": q_retry,
            "priority_breakdown": {"5": q_prio} if q_prio > 0 else {}
        }
