# TaskStorm System Architecture

This document defines the complete system architecture for TaskStorm, a Distributed Task Execution Platform. It outlines the service boundaries, component interactions, consistency models, and the architectural principles guiding the implementation.

## 1. System Overview

TaskStorm is designed to decouple task submission from execution. Clients submit tasks via a FastAPI-based HTTP API. The API validates the requests and persists the task metadata and payloads into Redis, which serves as the message broker and state store. Independent worker processes continuously poll or block on Redis queues, claim tasks concurrently using asyncio, execute them, and report the outcomes back to Redis. 

## 2. Service Boundaries

The system is partitioned into the following discrete services:

- **API Service**: A stateless FastAPI application responsible for handling RESTful endpoints (task submission, querying, cancellation) and Server-Sent Events (SSE) for real-time state updates. The API Service never executes long-running tasks directly; its primary role is to enforce input validation, manage task lifecycle transitions, and enqueue work.
- **Worker Service**: Independent Python processes that pull tasks from Redis queues. Workers use `asyncio` to execute multiple tasks concurrently. They manage their own lifecycle, including claiming tasks, maintaining leases (heartbeats), and handling execution outcomes (success, failure, retry).
- **Scheduler Service**: A background control loop (which can run within the API process or as a lightweight standalone service) responsible for promoting delayed or scheduled tasks. It monitors a Redis sorted set containing future tasks and moves them to the active queue when their scheduled execution time arrives.
- **Recovery Service**: A background process dedicated to fault tolerance. It detects stale workers (via heartbeat expiry), identifies expired task leases, and reclaims abandoned tasks, safely re-enqueuing them for execution.
- **Redis**: A single Redis instance that serves multiple roles: message broker (queues), task state store (Hash structures), coordination layer (distributed locks/leases), and event bus (Pub/Sub).

## 3. Task Lifecycle State Machine

Tasks in TaskStorm follow a strict lifecycle, managed by a formal state machine. 

### Valid States
- **PENDING**: Task is scheduled for the future but not yet ready for execution.
- **QUEUED**: Task is ready and waiting in a queue to be claimed by a worker.
- **RUNNING**: Task has been claimed by a worker and is currently executing.
- **RETRYING**: Task execution failed but retries remain; waiting for a backoff period before re-queueing.
- **COMPLETED**: Task executed successfully (Terminal state).
- **FAILED**: Task execution failed and no retries remain, or it was recovered after lease expiry without retries (Terminal state).
- **DLQ**: Dead Letter Queue; task failed all retries and is set aside for manual inspection (Terminal state).
- **CANCELLED**: Task was explicitly aborted before or during execution (Terminal state).

### State Diagram

```text
    +-------------------------------------------------------------+
    |                                                             |
    v                                                             |
[PENDING] --(API Enqueues)--> [QUEUED] --(Worker Claims)--> [RUNNING]
    |                            |                               |
 (API Cancels)             (API Cancels)                         |
    |                            |                               |
    +------> [CANCELLED] <-------+                     (Worker Succeeds)
                 ^                                               |
                 |                                               v
            (API Cancels)                                   [COMPLETED]
                 |
                 |
[RETRYING] ------+
    ^    |
    |    +--(Retry Delay Elapsed)--> [QUEUED]
    |                                   ^
 (Worker Fails, Retries Remain)         |
    |                                   |
 [RUNNING] -----------------------------+
    |                                   |
 (Worker Fails, No Retries)       (Manual Retry via API)
 (Lease Expired, Recovered)             |
    |                                   |
    v                                   |
 [FAILED] --(Max Retries Exhausted)--> [DLQ]
    |                                   |
    +-------(Manual Retry via API)------+
```

### Transition Enforcement
Illegal transitions must be explicitly rejected by a transition validator implemented in code. For example, a task cannot transition from `COMPLETED` to `RUNNING`. Any operation that mutates state must validate the current state against the requested state based on the rules above.

## 4. Delivery Semantics

TaskStorm guarantees **at-least-once delivery** coupled with **idempotent processing**.

- **At-Least-Once Delivery**: The system ensures that a successfully enqueued task will be executed by a worker. In the event of worker crashes, network partitions, or lease timeouts, the Recovery Service will requeue the task, guaranteeing it is not lost.
- **Idempotency**: Because a task may be requeued (e.g., if a worker completes the task but crashes before acknowledging it to Redis), the system explicitly acknowledges that **duplicate execution is possible**. Task handlers must be written idempotently so that executing the same task multiple times yields the same final system state.
- **Why not exactly-once?**: Exactly-once processing in distributed systems is theoretically impossible without strict, cross-system distributed transactions (e.g., two-phase commit), which degrade performance and are not supported by the chosen tech stack. Claiming exactly-once without such mechanisms is a fallacy. TaskStorm relies on idempotent application logic to simulate exactly-once side effects.

## 5. Consistency Model

To maintain a coherent state across distributed components:

- **Single Source of Truth**: Redis is the authoritative store for task state, metadata, and logs during the task's execution lifecycle.
- **Atomic Operations**: State transitions and queue manipulations are executed using Redis Lua scripts. This ensures atomicity and prevents race conditions (e.g., split-brain scenarios where two workers attempt to claim the same task).
- **Lease-Based Ownership**: When a worker claims a task, it acquires a lease. This lease grants exclusive rights to modify the task's state. The worker must periodically renew this lease (heartbeat) to maintain ownership.
- **Server-Side Validation**: All state-mutating operations validate the lease on the server side (within Lua scripts) before applying changes, ensuring that a worker whose lease has expired cannot overwrite state changes made by a new owner.

## 6. Communication Patterns

TaskStorm utilizes several communication patterns tailored to specific needs:

- **REST API**: Used by clients for CRUD operations—submitting tasks, querying task status, cancelling tasks, and triggering manual retries.
- **Server-Sent Events (SSE)**: Provides one-way, real-time event streaming to clients, allowing them to react to state changes without polling.
- **Redis Pub/Sub**: Internal event distribution mechanism. Workers and API nodes publish lifecycle events (e.g., `task.completed`, `task.failed`) to specific channels, which are consumed by SSE endpoints and logging services.
- **Redis Sorted Sets (ZSET)**: Used for scheduling delayed tasks. The score represents the UNIX timestamp when the task should become active.
- **Redis Lists / Sorted Sets**: Active queues are implemented using Redis Lists for FIFO ordering, or ZSETs if priority-based dequeuing is required.

## 7. Concurrency Model

The Worker Service achieves high throughput via asynchronous concurrency:

- **Asyncio Concurrency**: A single worker process uses Python's `asyncio` event loop to execute multiple I/O-bound tasks concurrently. This avoids the overhead of OS-level context switching.
- **WORKER_CONCURRENCY**: A configurable parameter that dictates the maximum number of concurrent tasks a single worker process can handle simultaneously.
- **Distinction from Multiprocessing**: Async concurrency is not CPU parallelism. CPU-bound tasks will block the event loop and degrade performance. CPU parallelism is achieved by running multiple worker processes (scaling out), not by increasing `WORKER_CONCURRENCY`.

## 8. Scalability

- **Horizontal Worker Scaling**: Workers are stateless (their state is in Redis) and can be scaled independently. In a Docker Compose environment, this is as simple as `docker compose up --scale worker=N`.
- **API Scaling**: The API Service is completely stateless and can be scaled horizontally behind a load balancer.
- **Redis Bottleneck**: Redis serves as the central coordination point. While Redis is highly performant (capable of 100k+ ops/sec), it is the theoretical bottleneck of the system. For the scope of this project, a single Redis instance is both acceptable and optimal.

## 9. Security Model

Security is enforced at the application boundary and configuration level:

- **Input Validation**: All incoming API requests are strictly validated using Pydantic models. Malformed payloads are rejected immediately.
- **Payload Size Limits**: Task payloads are restricted in size to prevent memory exhaustion and Redis bloat.
- **No Arbitrary Code Execution**: Task payloads contain structured data referencing pre-registered task handlers, not executable code (e.g., no `eval` or pickling of functions).
- **Internal Infrastructure**: The Redis instance is placed on an internal network and is never exposed directly to the public internet.
- **CORS Configuration**: The API enforces Cross-Origin Resource Sharing (CORS) policies to restrict which client origins can interact with the system.
- **Configuration**: Sensitive values are managed via environment variables and `.env` files, never hardcoded.
- **Error Sanitization**: API responses sanitize internal exceptions to prevent leaking stack traces or sensitive infrastructure details to clients.

## 10. Component Interaction Diagram

```text
  [Client]                           [API Service]                     [Redis]                        [Worker Service]
     |                                     |                              |                                  |
     |--- 1. POST /tasks (submit) -------->|                              |                                  |
     |                                     |--- 2. Lua: Create Task ----->|                                  |
     |                                     |       & LPUSH queue          |                                  |
     |<-- 3. 201 Created (task_id) --------|                              |                                  |
     |                                     |                              |<--- 4. BRPOP / Lua Claim Task ---|
     |                                     |                              |                                  |
     |                                     |                              |--- 5. Return Task Data --------->|
     |                                     |                              |                                  |
     |                                     |                              |                                  |--- 6. Execute Task (asyncio)
     |                                     |                              |                                  |
     |                                     |                              |<--- 7. EXPIRE (Heartbeat) -------|
     |                                     |                              |                                  |
     |                                     |                              |<--- 8. Lua: Set COMPLETED -------|
     |                                     |                              |       & PUBLISH event            |
     |                                     |                              |                                  |
     |--- 9. GET /tasks/events (SSE) ----->|                              |                                  |
     |                                     |--- 10. SUBSCRIBE event ----->|                                  |
     |<-- 11. Event stream (COMPLETED) ----|                              |                                  |
     |                                     |                              |                                  |
```
