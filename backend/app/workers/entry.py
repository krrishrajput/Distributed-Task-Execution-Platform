import asyncio
import signal
from app.core.config import Settings
from app.core.logging import configure_logging, get_logger
from app.core.redis import get_redis, close_redis
from app.queue.task_queue import TaskQueue
from app.workers.runtime import WorkerRuntime

logger = get_logger(__name__)

async def main():
    config = Settings()
    configure_logging(config.LOG_LEVEL)
    
    redis = await get_redis(config.REDIS_URL)
    task_queue = TaskQueue(redis, config)
    runtime = WorkerRuntime(config, redis, task_queue)
    
    loop = asyncio.get_event_loop()
    
    def handle_sigterm():
        logger.info("Received SIGTERM, initiating shutdown...")
        asyncio.create_task(runtime.shutdown())
        
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, handle_sigterm)
    
    try:
        await runtime.start()
        # Keep running until runtime stops
        while runtime.running:
            await asyncio.sleep(1)
    finally:
        await close_redis()

if __name__ == "__main__":
    asyncio.run(main())
