from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    REDIS_URL: str = "redis://localhost:6379/0"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    WORKER_CONCURRENCY: int = 10
    TASK_LEASE_DURATION_SECONDS: int = 60
    HEARTBEAT_INTERVAL_SECONDS: int = 5
    HEARTBEAT_UNHEALTHY_THRESHOLD: int = 15
    HEARTBEAT_OFFLINE_THRESHOLD: int = 30
    TASK_MAX_RETRIES: int = 3
    TASK_RETRY_BASE_DELAY: float = 2.0
    TASK_RETRY_MAX_DELAY: float = 300.0
    TASK_RESULT_TTL_SECONDS: int = 86400
    IDEMPOTENCY_KEY_TTL_SECONDS: int = 86400
    MAX_PAYLOAD_SIZE_BYTES: int = 1048576
    SCHEDULER_INTERVAL_SECONDS: float = 1.0
    RECOVERY_INTERVAL_SECONDS: float = 10.0
    PRIORITY_AGING_INTERVAL_SECONDS: float = 60.0
    PRIORITY_AGING_AMOUNT: int = 1
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"

config = Settings()
