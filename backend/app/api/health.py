from fastapi import APIRouter, Depends, Response
from datetime import datetime, timezone
from app.core.redis import get_redis, get_redis_client, health_check
from app.core.config import config
from redis.asyncio import Redis

router = APIRouter(tags=["health"])

@router.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@router.get("/live")
async def liveness():
    return {"status": "alive"}

@router.get("/ready")
async def readiness(
    response: Response,
    redis: Redis = Depends(get_redis_client)
):
    is_healthy = await health_check(redis)
    if not is_healthy:
        response.status_code = 503
        return {"status": "unhealthy", "redis": "disconnected"}
    return {"status": "ready", "redis": "connected"}
