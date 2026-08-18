# TaskStorm Redis Data Model

This document defines all Redis data structures, key patterns, and atomic operations (Lua scripts) used by TaskStorm for distributed task execution.

## Key Namespace Convention

All keys in TaskStorm use the `ts:` prefix to isolate data within a shared Redis instance. Colons (`:`) are used as hierarchical separators.

## Data Structures

### 1. Task State (Hash)
**Key Pattern:** `ts:task:{task_id}`

The source of truth for a task's state.

**Fields:**
- `id` (string): UUID of the task.
- `type` (string): Type of task (e.g., `email.send`, `image.process`).
- `payload` (string): JSON-serialized input data.
- `priority` (integer): Execution priority (lower number = higher priority).
- `status` (string): Current state (`PENDING`, `SCHEDULED`, `RUNNING`, `COMPLETED`, `FAILED`, `RETRYING`, `DLQ`).
- `created_at` (float): Unix timestamp.
- `updated_at` (float): Unix timestamp.
- `scheduled_at` (float): Unix timestamp for delayed tasks (optional).
- `worker_id` (string): ID of the worker currently executing the task.
- `attempt` (integer): Current execution attempt number (starts at 1).
- `max_retries` (integer): Maximum allowed attempts before DLQ.
- `lease_id` (string): UUID of the current execution lease.
- `lease_expires_at` (float): Unix timestamp.
- `result` (string): JSON-serialized execution result.
- `error` (string): JSON-serialized error details if failed.
- `idempotency_key` (string): Optional key for deduplication.
- `execution_duration_ms` (integer): Duration of execution.
- `started_at` (float): Unix timestamp when execution began.
- `completed_at` (float): Unix timestamp when execution finished or failed.
- `state_history` (string): JSON array of state transitions.
- `retry_history` (string): JSON array of retry details.

**TTL:** Completed or failed tasks expire after a configurable retention period (default 24h).

### 2. Priority Queue (Sorted Set)
**Key Pattern:** `ts:queue:priority`

The main queue for executable tasks.

**Members:** `task_id`
**Score:** `(priority * 1e12) + enqueue_timestamp_ns`

This composite score encodes priority levels while maintaining FIFO ordering within the same priority level. Priority 1 (highest) yields lower scores, prioritizing them during `ZPOPMIN`.

*Starvation Prevention:* Implement priority aging. A background process periodically decrements the scores of long-waiting, low-priority tasks, allowing them to eventually surface.

### 3. Delayed/Scheduled Tasks (Sorted Set)
**Key Pattern:** `ts:queue:scheduled`

Tasks scheduled for future execution.

**Members:** `task_id`
**Score:** `scheduled_at_unix_timestamp`

A scheduler component continuously polls this set, querying for tasks where `score <= current_unix_timestamp`. Matching tasks are moved to `ts:queue:priority`.

### 4. Active Tasks (Set)
**Key Pattern:** `ts:active_tasks`

A global index of all tasks currently in the `RUNNING` state.

**Members:** `task_id`

### 5. Worker-Task Mapping (Set)
**Key Pattern:** `ts:worker:{worker_id}:tasks`

Tracks the specific tasks owned by an individual worker.

**Members:** `task_id`

### 6. Worker Registry (Hash)
**Key Pattern:** `ts:worker:{worker_id}`

Maintains metadata and health status for active workers.

**Fields:**
- `id` (string): Worker UUID.
- `status` (string): e.g., `IDLE`, `BUSY`, `DRAINING`.
- `last_heartbeat` (float): Unix timestamp.
- `started_at` (float): Unix timestamp.
- `active_tasks` (integer): Number of concurrent tasks.
- `completed_tasks` (integer): Lifetime completed count.
- `failed_tasks` (integer): Lifetime failed count.
- `hostname` (string): Host machine name.
- `pid` (integer): Process ID.
- `concurrency` (integer): Maximum concurrent tasks allowed.

**TTL:** Worker entries expire if a heartbeat renewal is not received within a timeout window (e.g., 30s).

### 7. Worker Set (Set)
**Key Pattern:** `ts:workers`

Global index of all registered workers for enumeration.

**Members:** `worker_id`

### 8. Lease (Hash)
**Key Pattern:** `ts:lease:{task_id}`

Provides distributed locking to ensure only one worker processes a task at a time.

**Fields:**
- `worker_id` (string): Owner of the lease.
- `lease_id` (string): UUID unique to this specific lease acquisition.
- `acquired_at` (float): Unix timestamp.
- `expires_at` (float): Unix timestamp.
- `renewals` (integer): Counter of lease extensions.

**TTL:** Set to the `lease_duration`. If the key is absent, the lease has expired.

### 9. Idempotency Keys (String)
**Key Pattern:** `ts:idempotency:{idempotency_key}`

Ensures tasks are only submitted once for a given business operation.

**Value:** `task_id`
**TTL:** Configurable (default 24h).

Using `SET NX` guarantees atomicity. The first client to set the key successfully submits the task; subsequent clients retrieve the existing `task_id`.

### 10. Dead Letter Queue (List)
**Key Pattern:** `ts:dlq`

Tasks that have exhausted all retries or failed fatally.

**Members:** `task_id` (pushed via `RPUSH`)

### 11. Event Stream (Pub/Sub)
**Channel:** `ts:events`

Real-time notification system for state changes.

**Message Format:** JSON containing `event_type`, `task_id`, `worker_id`, `timestamp`, `data`.

### 12. Metrics Counters (String)
**Key Patterns:**
- `ts:metrics:tasks_submitted`
- `ts:metrics:tasks_completed`
- `ts:metrics:tasks_failed`
- `ts:metrics:tasks_retried`
- `ts:metrics:tasks_dlq`
- `ts:metrics:tasks_recovered`

Used with `INCR` to track global operational metrics.

### 13. Retry Queue (Sorted Set)
**Key Pattern:** `ts:queue:retry`

Tasks waiting for a backoff delay before their next attempt.

**Members:** `task_id`
**Score:** `next_retry_timestamp`

The scheduler process polls this queue alongside `ts:queue:scheduled`.

---

## Atomic Operations (Lua Scripts)

Given Redis' single-threaded nature, Lua scripts guarantee atomicity for complex state transitions. This prevents race conditions common in distributed systems.

### 1. `claim_task.lua`
**Process:**
1. Execute `ZPOPMIN` on `ts:queue:priority` to pop the highest priority task.
2. If empty, return `nil`.
3. Set task status to `RUNNING` in `ts:task:{task_id}`.
4. Create the lease hash at `ts:lease:{task_id}` and set its TTL.
5. Add `task_id` to `ts:active_tasks`.
6. Add `task_id` to `ts:worker:{worker_id}:tasks`.
7. Return task metadata and the new `lease_id`.

**Race Condition Prevented:** Multiple workers attempting to pull the same task simultaneously. Atomicity ensures a task is dequeued and locked (leased) in a single step, preventing double execution.

### 2. `complete_task.lua`
**Process:**
1. Check `ts:lease:{task_id}` to verify the provided `lease_id` matches the stored one. If it doesn't match, reject the operation.
2. Update `ts:task:{task_id}`: set status to `COMPLETED`, save `result`, and set `completed_at`.
3. Remove `task_id` from `ts:active_tasks`.
4. Delete `ts:lease:{task_id}`.
5. Remove `task_id` from `ts:worker:{worker_id}:tasks`.
6. Increment `ts:metrics:tasks_completed`.

**Race Condition Prevented:** Stale worker protection. If a worker hangs and loses its lease, another worker might pick up the task. When the original worker finally wakes up and tries to complete it, the script rejects the completion because the original worker's `lease_id` is invalid, preventing it from overwriting the valid result.

### 3. `fail_task.lua`
**Process:**
1. Verify `lease_id` ownership (similar to completion).
2. Check `attempt` against `max_retries` in task state.
3. Update `ts:task:{task_id}`: save `error`, update `status` to `RETRYING` or `FAILED`.
4. If retrying: calculate backoff, add to `ts:queue:retry`, update metrics.
5. If failing permanently: push to `ts:dlq`, update metrics.
6. Remove from `ts:active_tasks` and `ts:worker:{worker_id}:tasks`.
7. Delete `ts:lease:{task_id}`.

**Race Condition Prevented:** Prevents a stale worker from corrupting retry logic or marking a successfully recovered task as failed.

### 4. `renew_lease.lua`
**Process:**
1. Verify the provided `lease_id` matches `ts:lease:{task_id}`.
2. If matching, execute `EXPIRE` on `ts:lease:{task_id}` to extend the TTL.
3. Increment the `renewals` field in the lease hash.

**Race Condition Prevented:** Prevents a worker from accidentally renewing a lease that has already expired and been re-acquired by a different worker.

### 5. `recover_task.lua`
**Process:**
1. Verify `ts:lease:{task_id}` does not exist. (If it exists, the task is actively leased and should not be recovered).
2. Read current task state. If not `RUNNING`, abort.
3. Update task state: increment `attempt`, reset `status` to `PENDING`.
4. Remove from previous worker's task set (if known).
5. Add back to `ts:queue:priority`.
6. Record a recovery event in `retry_history`.
7. Increment `ts:metrics:tasks_recovered`.

**Race Condition Prevented:** Prevents "split-brain" recovery where the recovery process and a legitimate worker contend for the task. The strict check for the absence of the lease key ensures only genuinely orphaned tasks are recovered.

---

## Cleanup Strategy

- **Completed/Failed Tasks:** Handled natively by Redis TTL on the `ts:task:{task_id}` hash.
- **Worker Entries:** Expire natively if heartbeats cease, via TTL on `ts:worker:{worker_id}`.
- **Idempotency Keys:** Handled natively by Redis TTL.
- **Leases:** Handled natively by Redis TTL.
- **Metrics:** Persist indefinitely (no TTL).
- **Queues/Sets:** Explicit removals occur during state transitions (e.g., removing from active set upon completion).
