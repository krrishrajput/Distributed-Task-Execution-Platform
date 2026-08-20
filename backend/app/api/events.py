from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from app.events.subscriber import EventSubscriber
from app.core.redis import get_redis, get_redis_client
from app.core.config import config
from redis.asyncio import Redis
import asyncio
import json

router = APIRouter(prefix="/api/v1", tags=["events"])

async def event_streamer(redis: Redis, request: Request):
    subscriber = EventSubscriber(redis)
    await subscriber.subscribe()
    try:
        async for event in subscriber.event_generator():
            if await request.is_disconnected():
                break
            yield f"data: {event.model_dump_json()}\n\n"
    except asyncio.CancelledError:
        pass

@router.get("/events")
async def event_stream(
    request: Request,
    redis: Redis = Depends(get_redis_client)
):
    return StreamingResponse(event_streamer(redis, request), media_type="text/event-stream")
