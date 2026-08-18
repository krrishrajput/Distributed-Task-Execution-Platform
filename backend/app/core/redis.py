from redis.asyncio import Redis, ConnectionPool
from typing import Optional

_redis_pool: Optional[ConnectionPool] = None

async def get_redis(url: str) -> Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(url, decode_responses=True)
    return Redis(connection_pool=_redis_pool)

async def close_redis() -> None:
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None

async def health_check(redis: Redis) -> bool:
    try:
        return await redis.ping()
    except Exception:
        return False
from app.core.config import config
async def get_redis_client() -> Redis:
    return await get_redis(config.REDIS_URL)

