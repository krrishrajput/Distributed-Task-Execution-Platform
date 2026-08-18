import asyncio
import json
from typing import AsyncGenerator
from redis.asyncio import Redis
from app.models.events import Event
from app.core.logging import get_logger

logger = get_logger(__name__)

class EventSubscriber:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.pubsub = self.redis.pubsub()

    async def subscribe(self):
        await self.pubsub.subscribe("ts:events")

    async def event_generator(self) -> AsyncGenerator[Event, None]:
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        yield Event(**event_data)
                    except Exception as e:
                        logger.error(f"Failed to parse event: {e}")
        finally:
            await self.pubsub.unsubscribe("ts:events")
