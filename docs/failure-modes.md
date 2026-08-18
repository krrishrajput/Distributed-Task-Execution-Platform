# TaskStorm Failure Modes and System Resilience

This document outlines the actual behavior of the TaskStorm platform under various failure conditions. It details how failures are detected, their impact, recovery mechanisms, data consistency guarantees, and known edge cases. This describes what the system actually does, not theoretical claims.

## 1. Worker Crashes During Task Execution

1. **Scenario**: A worker process terminates abruptly (e.g., `kill -9`, OOM killer, instance crash) while actively processing a task.
2. **Detection**: The worker's periodic heartbeat to Redis stops. The task's lease expires after the configured `lease_duration`.
3. **Impact**: The crashed worker is lost. The specific task it was executing remains in the `active` queue but is no longer being processed.
4. **Recovery**: The recovery service (running in the API tier) periodically scans for tasks with expired leases. It detects this task, clears its ownership, and requeues it for another worker to claim.
5. **Data consistency**: At-least-once delivery semantics apply. Any partial work done by the crashed worker is lost. The task will be executed again from scratch.
6. **Edge cases**: If the crash happens after the task logic completes but before the `complete_task` API call (or Redis acknowledgment) succeeds, the task may execute twice.

## 2. Worker Crashes After Execution But Before Acknowledgement

1. **Scenario**: The task handler executes successfully, but the worker crashes before it can acknowledge completion to Redis.
2. **Detection**: The task lease expires, as the heartbeat stops and the completion was not recorded.
3. **Impact**: The task appears incomplete to the system despite the actual work being done.
4. **Recovery**: The recovery service detects the expired lease and requeues the task. Another worker claims it.
5. **Data consistency**: The task executes again. **This is why TaskStorm provides at-least-once delivery, not exactly-once.** Idempotent task handlers are strictly required to tolerate this scenario.
6. **Edge cases**: The duplicate execution might fail if the underlying work was not truly idempotent, leading to a DLQ entry for a task that actually succeeded the first time.

## 3. Lease Expires While Worker Is Still Running

1. **Scenario**: A worker is actively processing a task but becomes exceptionally slow (e.g., GC pause, CPU starvation, blocking I/O stall), causing its lease to expire before completion.
2. **Detection**: The recovery service identifies the task's lease timestamp as being older than the current time minus `lease_duration`.
3. **Impact**: The task is considered abandoned by the system, though the original worker is still executing it.
4. **Recovery**: The task is requeued. A second worker claims it and begins execution concurrently with the original worker.
5. **Data consistency**: When the original worker finally finishes and attempts to acknowledge completion, the request is REJECTED because the `lease_id` provided does not match the new `lease_id` in Redis. Only one worker's result (the second one, assuming it completes) is accepted.
6. **Edge cases**: Both workers execute the task logic. Depending on the task's external side effects, this concurrent execution might cause resource contention or partial state mutations in external systems.

## 4. Stale Worker Attempts Completion

1. **Scenario**: A worker held a valid lease, lost it due to expiry (and recovery gave the task to a new worker), and then the original worker attempts to complete the task.
2. **Detection**: A Lua script executed during `complete_task` atomically verifies the `lease_id`.
3. **Impact**: The stale worker's completion request is denied.
4. **Recovery**: The Lua script rejects the operation. The stale worker logs the rejection and discards its computed result.
5. **Data consistency**: The system state remains consistent. The task state is exclusively managed by the worker holding the current valid lease.
6. **Edge cases**: External side effects performed by the stale worker cannot be rolled back by TaskStorm.

## 5. Heartbeat Loss Without Worker Crash

1. **Scenario**: A network partition occurs between a worker and the Redis cluster. The worker process is healthy but cannot send heartbeats.
2. **Detection**: The system marks the worker as UNHEALTHY after a threshold of missed heartbeats.
3. **Impact**: If the partition persists, the worker is marked OFFLINE. Any active tasks held by this worker will eventually have their leases expire.
4. **Recovery**: Tasks with expired leases are requeued by the recovery service. When the network partition resolves, the worker attempts to resume. It detects that its tasks' leases have been invalidated and stops processing those tasks.
5. **Data consistency**: Tasks are safely moved to other workers. The isolated worker gracefully abandons its work once connectivity returns.
6. **Edge cases**: During the partition, the isolated worker continues to execute its current task, oblivious to the fact that it has lost the lease. This leads to the concurrent execution scenario described in #3.

## 6. Redis Connection Interruption

1. **Scenario**: The Redis instance becomes temporarily unavailable (e.g., failover, restart, network issue).
2. **Detection**: The API and worker clients encounter connection errors and timeouts.
3. **Impact**: The API returns HTTP 503 Service Unavailable for new task submissions. Workers fail to pull new tasks or acknowledge completions.
4. **Recovery**: Workers and API services enter a backoff-retry loop for Redis operations. Once Redis is available, operations resume.
5. **Data consistency**: No tasks are lost, as all authoritative state is persisted in Redis.
6. **Edge cases**: In-flight tasks that a worker completed but couldn't acknowledge will eventually hit lease expiry and be duplicated once the system recovers.

## 7. API Service Restart

1. **Scenario**: The API service process crashes or is restarted.
2. **Detection**: Load balancers detect the failure and route traffic to other instances, or process managers restart the service.
3. **Impact**: In-progress HTTP requests receive errors (e.g., 502 Bad Gateway). SSE connections drop.
4. **Recovery**: Clients must retry failed API requests and reconnect SSE streams. The scheduler and recovery background loops restart fresh in the new process.
5. **Data consistency**: No task state is lost because the API service is stateless; all state resides in Redis.
6. **Edge cases**: A restart during a scheduler loop might slightly delay task promotion, but since the promotion is idempotent, it recovers gracefully upon restart.

## 8. Duplicate Task Submission (Same Idempotency Key)

1. **Scenario**: A client application submits the exact same task twice, using the same `idempotency_key`.
2. **Detection**: Task creation uses a Redis `SET NX` command.
3. **Impact**: The system detects the existing key.
4. **Recovery**: The second submission does not create a new task. Instead, it returns the existing `task_id` with an HTTP 200 OK (rather than 201 Created).
5. **Data consistency**: Exactly one task is created. If concurrent submissions occur, the Redis atomic `SET NX` handles the race condition.
6. **Edge cases**: If the original task has already completed, the duplicate submission will simply return the identifier of the completed task.

## 9. Concurrent Task Claim

1. **Scenario**: Two or more workers attempt to claim the exact same task from the queue at the exact same microsecond.
2. **Detection**: Claiming a task relies on a Redis `ZPOPMIN` command within a Lua script.
3. **Impact**: None. The operation is inherently atomic.
4. **Recovery**: Only one worker successfully pops the task. The other worker(s) receive a `nil` response and proceed to poll for the next available task.
5. **Data consistency**: No split-brain or duplicate assignment is possible at the claim stage.
6. **Edge cases**: Negligible. Redis guarantees single-threaded execution of the Lua script.

## 10. Retry Storm

1. **Scenario**: A downstream dependency fails, causing a massive number of tasks to fail and be scheduled for retry simultaneously.
2. **Detection**: Workers process tasks, tasks fail, and are pushed to the scheduled retry queue.
3. **Impact**: A large backlog of scheduled tasks forms.
4. **Recovery**: The system utilizes exponential backoff with jitter for retries. This spreads the retry times across a wider window, preventing all tasks from becoming active at the exact same moment. Workers naturally load-balance the influx via atomic claims.
5. **Data consistency**: Task processing slows down, but no data is lost or corrupted.
6. **Edge cases**: If the failure is sustained, tasks will eventually exhaust their retry limits and move to the Dead Letter Queue (DLQ).

## 11. Recovery Service Restart

1. **Scenario**: The background loop responsible for recovering expired leases crashes and restarts.
2. **Detection**: Process supervision restarts the loop.
3. **Impact**: Recovery of stuck tasks is temporarily halted.
4. **Recovery**: The loop restarts and immediately scans all active tasks for expired leases.
5. **Data consistency**: The recovery operation is idempotent. Re-recovering an already-recovered task is safe.
6. **Edge cases**: There is a small window bounded by the downtime and scan interval where expired leases are not detected, delaying the requeuing of failed tasks.

## 12. Scheduler Restart

1. **Scenario**: The background scheduler loop that promotes delayed/retry tasks to the active queue restarts.
2. **Detection**: Process supervision restarts the loop.
3. **Impact**: Promotion of scheduled tasks is temporarily paused.
4. **Recovery**: The scheduler restarts and scans the scheduled queue (ZSET) for any tasks whose scheduled execution time is in the past.
5. **Data consistency**: It promotes them to the active queue. This operation is idempotent; state checks prevent re-promoting an already-promoted task.
6. **Edge cases**: Tasks scheduled for immediate execution during the downtime will be slightly delayed until the scheduler resumes.

## 13. DLQ Overflow

1. **Scenario**: A high volume of tasks exhausts their retry limits and are moved to the Dead Letter Queue (DLQ).
2. **Detection**: Monitoring on DLQ size metrics alerts operators.
3. **Impact**: The DLQ grows large, consuming Redis memory.
4. **Recovery**: DLQ tasks have a TTL-based expiry (configurable retention period). The API provides endpoints for listing DLQ contents and manually requeuing them once the underlying issue is fixed.
5. **Data consistency**: There is intentional **no automatic DLQ processing**. DLQ implies a terminal failure requiring human investigation.
6. **Edge cases**: If operators ignore the DLQ, tasks will eventually expire via TTL and be permanently lost.

## 14. Priority Starvation

1. **Scenario**: The system receives a continuous, high-volume stream of high-priority tasks.
2. **Detection**: Low-priority tasks remain in the active queue indefinitely.
3. **Impact**: Low-priority tasks suffer severe latency.
4. **Recovery**: TaskStorm implements a priority aging mechanism. A background process periodically boosts the priority score of tasks that have been waiting in the queue beyond a certain threshold.
5. **Data consistency**: All tasks are eventually processed.
6. **Edge cases**: This is a documented limitation: under sustained, extreme high load, low-priority tasks may still wait significantly longer than expected despite aging.

---

## What We Don't Handle

TaskStorm is designed for practical resilience but has explicit boundaries. The following failure modes are **not** handled:

*   **Redis Data Loss**: In a single-node Redis setup (or a cluster without strict persistence/replication), a Redis crash may result in total loss of task state. We assume Redis is configured appropriately for the required durability tier.
*   **Total Network Partitions**: If network partitions isolate the Redis cluster from all workers and API services simultaneously, the entire system halts.
*   **Clock Skew Between Workers**: We mitigate this by using the Redis server time (via Lua `TIME`) for all lease evaluations, rather than relying on local worker clocks. However, extreme skew on API nodes could affect scheduling calculations.
*   **Infinite Task Execution**: Tasks that enter infinite loops or deadlocks inside the worker process are bounded by the `lease_duration`. They will be recovered and retried, but the stuck worker thread/process may remain stuck permanently unless the worker application implements internal timeouts or restarts.
