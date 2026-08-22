from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from enum import Enum
from typing import Optional, Any, List

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DLQ = "DLQ"
    CANCELLED = "CANCELLED"

TASK_TYPES = ["sleep", "cpu_simulation", "random_failure", "deterministic_failure", "lease_expiration", "eventual_success", "test"]

class TaskCreate(BaseModel):
    task_type: str
    payload: dict = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)
    max_retries: int = Field(default=3, ge=0, le=20, description='Number of retries allowed after initial execution')
    scheduled_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None

class StateTransition(BaseModel):
    from_status: TaskStatus
    to_status: TaskStatus
    timestamp: datetime
    worker_id: Optional[str] = None
    reason: Optional[str] = None

class RetryRecord(BaseModel):
    attempt: int
    error: str
    timestamp: datetime
    worker_id: str
    next_retry_at: Optional[datetime] = None

class Task(BaseModel):
    id: str
    task_type: str
    payload: dict
    priority: int
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None
    attempt: int
    max_retries: int
    lease_id: Optional[str] = None
    lease_expires_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    idempotency_key: Optional[str] = None
    execution_duration_ms: Optional[float] = None
    state_history: List[StateTransition]
    retry_history: List[RetryRecord]

    @field_validator("payload", mode="before")
    def coerce_empty_payload(cls, v):
        if isinstance(v, list) and len(v) == 0:
            return {}
        return v

    @field_validator("state_history", "retry_history", mode="before")
    def coerce_empty_lists(cls, v):
        if isinstance(v, dict) and len(v) == 0:
            return []
        return v

class TaskSummary(BaseModel):
    id: str
    task_type: str
    status: TaskStatus
    priority: int
    attempt: int
    worker_id: Optional[str] = None
    created_at: datetime
    execution_duration_ms: Optional[float] = None

VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
    TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {TaskStatus.COMPLETED, TaskStatus.RETRYING, TaskStatus.FAILED},
    TaskStatus.RETRYING: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
    TaskStatus.FAILED: {TaskStatus.DLQ, TaskStatus.QUEUED},
    TaskStatus.DLQ: {TaskStatus.QUEUED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.CANCELLED: set(),
}

def validate_transition(from_status: TaskStatus, to_status: TaskStatus) -> bool:
    return to_status in VALID_TRANSITIONS.get(from_status, set())
