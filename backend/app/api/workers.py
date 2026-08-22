from fastapi import APIRouter, Depends
from typing import List
from app.models.worker import WorkerInfo
from app.core.redis import get_redis, get_redis_client
from app.core.config import config
from redis.asyncio import Redis

router = APIRouter(prefix="/api/v1/workers", tags=["workers"])

@router.get("", response_model=List[WorkerInfo])
async def list_workers(
    redis: Redis = Depends(get_redis_client)
):
    worker_ids = await redis.smembers("ts:workers")
    workers = []
    
    if not worker_ids:
        return []
    
    keys = [f"ts:worker_info:{wid}" for wid in worker_ids]
    raw_data = await redis.mget(keys)
    
    for data in raw_data:
        if data:
            workers.append(WorkerInfo.model_validate_json(data))
            
    return workers
