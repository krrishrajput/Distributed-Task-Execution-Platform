from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class WorkerStatus(str, Enum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    DRAINING = "DRAINING"
    OFFLINE = "OFFLINE"

class WorkerInfo(BaseModel):
    worker_id: str
    status: WorkerStatus
    last_heartbeat: datetime
    started_at: datetime
    active_tasks: int
    completed_tasks: int
    failed_tasks: int
    hostname: str
    pid: int
    concurrency: int
    uptime_seconds: float
