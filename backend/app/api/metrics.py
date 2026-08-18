from fastapi import APIRouter, Depends
from app.metrics.collector import MetricsCollector
from app.core.redis import get_redis, get_redis_client
from app.core.config import config
from redis.asyncio import Redis

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

@router.get("")
async def get_metrics(
    redis: Redis = Depends(get_redis_client)
):
    collector = MetricsCollector(redis)
    return await collector.get_metrics()
