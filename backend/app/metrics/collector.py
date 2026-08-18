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
        
        return {
            "submitted": int(results[0] or 0),
            "completed": int(results[1] or 0),
            "failed": int(results[2] or 0),
            "queue_depth_priority": results[3],
            "queue_depth_scheduled": results[4],
            "queue_depth_retry": results[5],
            "active_tasks": results[6],
            "active_workers": results[7],
            "dlq_depth": results[8]
        }
