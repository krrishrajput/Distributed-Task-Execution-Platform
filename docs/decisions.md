# Architecture Decision Records (ADRs)

## ADR-001: Redis as Sole Coordination Layer
**Context**: Need a message broker, state store, and coordination mechanism.
**Decision**: Use Redis for all three.
**Rationale**: Redis provides atomic operations (Lua scripts), sorted sets for priority queues, pub/sub for events, hashes for state, and TTL for lease management — all in one system. Avoids operational complexity of multiple systems.
**Tradeoffs**: Single point of failure. No built-in durability guarantees (AOF/RDB help but aren't transactional). Acceptable for a demonstration system.
**Alternatives**: PostgreSQL (slower for queue operations), RabbitMQ (prohibited), separate systems for each concern (unnecessary complexity).

## ADR-002: at-least-once Delivery
**Context**: Need to choose delivery semantics.
**Decision**: at-least-once delivery with idempotent processing.
**Rationale**: Exactly-once requires distributed transactions (2PC) or log-based deduplication at every consumer. Too complex, too fragile. at-least-once is achievable with Redis atomics and lease-based ownership. Idempotent handlers on the consumer side prevent corruption from duplicate execution.
**Tradeoffs**: Tasks may execute more than once. Side effects must be idempotent or tolerable.

## ADR-003: Lease-Based Ownership
**Context**: Need to prevent split-brain when workers fail.
**Decision**: Every running task has a lease (worker_id + lease_id + expiry). All state-mutating operations verify lease ownership atomically.
**Rationale**: Heartbeats detect worker liveness but don't prevent stale writes. Leases provide a concrete ownership token that expires. Server-side validation (in Lua) ensures a worker that lost its lease cannot corrupt task state.
**Tradeoffs**: Lease duration is a tuning parameter. Too short → unnecessary recovery. Too long → slow failure detection.

## ADR-004: Lua Scripts for Atomic Operations
**Context**: Multiple Redis operations need to be atomic (claim, complete, fail, renew lease).
**Decision**: Use Redis Lua scripting for all multi-step atomic operations.
**Rationale**: Redis executes Lua scripts atomically — no other command runs between script operations. This eliminates TOCTOU races in claim/complete/fail flows.
**Tradeoffs**: Lua scripts block Redis during execution. Keep scripts short and avoid I/O.

## ADR-005: Sorted Set Priority Queue with Score Encoding
**Context**: Need a priority queue with FIFO within same priority.
**Decision**: Use Redis sorted set with score = priority * 1e12 + enqueue_timestamp_ns.
**Rationale**: Sorted sets provide O(log N) insertion and O(log N) pop-min. Encoding priority into the upper bits and timestamp into the lower bits gives natural priority ordering with FIFO tiebreaking.
**Tradeoffs**: Score precision limited by float64. Nanosecond timestamps within 1e12 range provide sufficient resolution.

## ADR-006: asyncio for Worker Concurrency
**Context**: Workers need to execute multiple tasks concurrently.
**Decision**: Use asyncio with configurable WORKER_CONCURRENCY (e.g., 20 concurrent tasks per worker process).
**Rationale**: Task handlers are primarily I/O-bound (simulated work). asyncio provides lightweight concurrency without the overhead of threads or processes. Not suitable for CPU-bound parallelism, which would require multiprocessing.
**Tradeoffs**: CPU-bound tasks block the event loop. Documented limitation. Real production system would use a process pool for CPU-bound work.

## ADR-007: SSE for Real-Time Events (not WebSockets)
**Context**: Dashboard needs real-time updates.
**Decision**: Server-Sent Events over WebSockets.
**Rationale**: SSE is simpler (HTTP, auto-reconnect, no custom protocol). Unidirectional (server→client) is sufficient for monitoring. Built-in browser support. Works through proxies and load balancers.
**Tradeoffs**: No client→server channel (not needed). Limited browser connection pool (6 per domain in HTTP/1.1).

## ADR-008: Heartbeats Separate from Leases
**Context**: Both heartbeats and leases track worker/task health.
**Decision**: Heartbeats track worker liveness. Leases track task ownership. They are independent mechanisms.
**Rationale**: Heartbeats answer: 'Is this worker alive?' Leases answer: 'Does this worker still own this task?' A worker can be alive but have lost a lease (slow processing). A lease can be valid but worker unhealthy (just barely within timing). Separating concerns allows independent tuning.

## ADR-009: Priority Aging for Starvation Prevention
**Context**: High-priority tasks can starve low-priority tasks indefinitely.
**Decision**: Implement periodic priority aging — decrement scores of tasks waiting beyond a threshold.
**Rationale**: Simple and predictable. Tasks that wait long enough eventually get promoted. Tunable via aging_interval and aging_amount.
**Tradeoffs**: Under sustained high load, aging is best-effort. Low-priority tasks may still wait significantly longer.

## ADR-010: No External Task Framework
**Context**: Could use Celery, BullMQ, etc.
**Decision**: Build from scratch using Redis primitives.
**Rationale**: Educational/portfolio purpose. Demonstrates understanding of distributed systems fundamentals. Full control over semantics.
**Tradeoffs**: Less battle-tested. More code to maintain. Acceptable for demonstration.

## ADR-011: Single Redis Instance
**Context**: Could use Redis Cluster or Sentinel.
**Decision**: Single Redis instance.
**Rationale**: Simplifies deployment and reasoning about consistency. Redis Cluster complicates Lua scripts (keys must hash to same slot). Sentinel adds operational complexity. Documented as a limitation.
**Tradeoffs**: Single point of failure. Not suitable for production at scale.

## ADR-012: Predefined Task Types Only
**Context**: Could allow arbitrary task code.
**Decision**: Only predefined, registered task types (sleep, cpu_simulation, random_failure, etc.).
**Rationale**: Security. Arbitrary code execution is a critical vulnerability. Predefined handlers are safe, testable, and deterministic.
**Tradeoffs**: Adding new task types requires code changes. Acceptable.
