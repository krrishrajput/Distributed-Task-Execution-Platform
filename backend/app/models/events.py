from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid

class EventType(str, Enum):
    TASK_QUEUED = "TASK_QUEUED"
    TASK_STARTED = "TASK_STARTED"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_RETRYING = "TASK_RETRYING"
    TASK_DLQ = "TASK_DLQ"
    TASK_RECOVERED = "TASK_RECOVERED"
    TASK_CANCELLED = "TASK_CANCELLED"
    WORKER_REGISTERED = "WORKER_REGISTERED"
    WORKER_HEARTBEAT_LOST = "WORKER_HEARTBEAT_LOST"
    WORKER_RECOVERED = "WORKER_RECOVERED"
    LEASE_EXPIRED = "LEASE_EXPIRED"

class Event(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime
    task_id: Optional[str] = None
    worker_id: Optional[str] = None
    details: dict = {}
