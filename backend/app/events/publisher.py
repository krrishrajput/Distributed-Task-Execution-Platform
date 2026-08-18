import json
from redis.asyncio import Redis
from app.models.events import Event

class EventPublisher:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def publish(self, event: Event):
        await self.redis.publish("ts:events", event.model_dump_json())
