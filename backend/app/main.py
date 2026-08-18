from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from app.core.config import config
from app.core.logging import configure_logging, get_logger
from app.core.redis import get_redis, close_redis
from app.api.tasks import router as tasks_router
from app.api.workers import router as workers_router
from app.api.metrics import router as metrics_router
from app.api.events import router as events_router
from app.api.health import router as health_router
from app.scheduler.scheduler import SchedulerService
from app.recovery.recovery import RecoveryService
from app.queue.task_queue import TaskQueue

logger = get_logger(__name__)
configure_logging(config.LOG_LEVEL)

app = FastAPI(
    title="TaskStorm API",
    version="1.0.0",
    description="Distributed Task Execution Platform API"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)
app.include_router(workers_router)
app.include_router(metrics_router)
app.include_router(events_router)
app.include_router(health_router)

scheduler_svc = None
recovery_svc = None

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up TaskStorm API")
    redis = await get_redis(config.REDIS_URL)
    task_queue = TaskQueue(redis, config)
    
    global scheduler_svc, recovery_svc
    scheduler_svc = SchedulerService(task_queue, config)
    recovery_svc = RecoveryService(task_queue, config)
    
    await scheduler_svc.start()
    await recovery_svc.start()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down TaskStorm API")
    if scheduler_svc:
        await scheduler_svc.stop()
    if recovery_svc:
        await recovery_svc.stop()
    
    await close_redis()
