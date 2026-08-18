import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from redis.asyncio import Redis, ConnectionPool
import asyncio
from typing import AsyncGenerator

from app.core.config import Settings
from app.queue.task_queue import TaskQueue

TEST_REDIS_URL = "redis://localhost:6379/15"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_settings() -> Settings:
    settings = Settings(
        REDIS_URL=TEST_REDIS_URL,
        TASK_LEASE_DURATION_SECONDS=60,
        TASK_MAX_RETRIES=3,
        TASK_RETRY_BASE_DELAY=0.1,
        TASK_RETRY_MAX_DELAY=1.0,
    )
    return settings

@pytest_asyncio.fixture
async def redis(test_settings: Settings) -> AsyncGenerator[Redis, None]:
    try:
        pool = ConnectionPool.from_url(test_settings.REDIS_URL, decode_responses=True)
        redis_client = Redis(connection_pool=pool)
        await redis_client.ping()
        await redis_client.flushdb()
        
        yield redis_client
        
        await redis_client.flushdb()
        await redis_client.close()
        await pool.disconnect()
    except Exception:
        # Fallback to in-memory FakeAsyncRedis with Lua scripting support
        import fakeredis.aioredis
        fake_client = fakeredis.aioredis.FakeRedis(decode_responses=True)
        await fake_client.flushdb()
        
        yield fake_client
        
        await fake_client.flushdb()
        await fake_client.close()

@pytest_asyncio.fixture
async def task_queue(redis: Redis, test_settings: Settings) -> TaskQueue:
    return TaskQueue(redis, test_settings)

@pytest_asyncio.fixture
async def async_client(redis: Redis, test_settings: Settings, monkeypatch) -> AsyncGenerator[AsyncClient, None]:
    import app.core.config
    import app.core.redis
    import app.main
    
    monkeypatch.setattr(app.core.config, "config", test_settings)
    monkeypatch.setattr(app.core.redis, "get_redis_client", lambda: redis)
    monkeypatch.setattr(app.core.redis, "get_redis", lambda url: redis)
    
    transport = ASGITransport(app=app.main.app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
