export enum TaskStatus {
  PENDING = 'PENDING',
  QUEUED = 'QUEUED',
  RUNNING = 'RUNNING',
  RETRYING = 'RETRYING',
  COMPLETED = 'COMPLETED',
  FAILED = 'FAILED',
  DLQ = 'DLQ',
  CANCELLED = 'CANCELLED'
}

export enum WorkerStatus {
  HEALTHY = 'HEALTHY',
  UNHEALTHY = 'UNHEALTHY',
  DRAINING = 'DRAINING',
  OFFLINE = 'OFFLINE'
}

export interface Task {
  id: string;
  task_type: string;
  status: TaskStatus;
  priority: number;
  payload: Record<string, any>;
  result?: Record<string, any> | null;
  error?: string | null;
  worker_id?: string | null;
  attempt: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface TaskCreate {
  task_type: string;
  payload?: Record<string, any>;
  priority?: number;
  max_retries?: number;
}

export interface WorkerInfo {
  worker_id: string;
  status: WorkerStatus;
  active_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  concurrency: number;
  last_heartbeat: string;
  started_at: string;
  queues: string[];
}

export interface Metrics {
  throughput: number;
  queue_depth: number;
  latency_p50: number;
  latency_p95: number;
  latency_p99: number;
  avg_execution_duration: number;
  retry_rate: number;
  failure_rate: number;
  worker_utilization: number;
  recovery_count: number;
  dlq_count: number;
  scheduled_count: number;
  retry_queue_count: number;
  priority_breakdown: Record<string, number>;
}

export enum EventType {
  TASK_CREATED = 'TASK_CREATED',
  TASK_QUEUED = 'TASK_QUEUED',
  TASK_STARTED = 'TASK_STARTED',
  TASK_COMPLETED = 'TASK_COMPLETED',
  TASK_FAILED = 'TASK_FAILED',
  TASK_RETRIED = 'TASK_RETRIED',
  TASK_DLQ = 'TASK_DLQ',
  TASK_CANCELLED = 'TASK_CANCELLED',
  WORKER_JOINED = 'WORKER_JOINED',
  WORKER_HEARTBEAT = 'WORKER_HEARTBEAT',
  WORKER_OFFLINE = 'WORKER_OFFLINE',
  QUEUE_PAUSED = 'QUEUE_PAUSED',
  QUEUE_RESUMED = 'QUEUE_RESUMED'
}

export interface SystemEvent {
  event_id: string;
  event_type: EventType;
  timestamp: string;
  task_id?: string;
  worker_id?: string;
  details?: Record<string, any>;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}
