-- KEYS: task_key, lease_key, active_tasks_key, worker_tasks_key, retry_queue_key, dlq_key, metrics_failed, events_channel
-- ARGS: task_id, worker_id, lease_id, error_msg, timestamp_str, retry_delay_score, timestamp_ms

local task_key = KEYS[1]
local lease_key = KEYS[2]
local active_tasks_key = KEYS[3]
local worker_tasks_key = KEYS[4]
local retry_queue_key = KEYS[5]
local dlq_key = KEYS[6]
local metrics_failed = KEYS[7]
local events_channel = KEYS[8]

local task_id = ARGV[1]
local worker_id = ARGV[2]
local lease_id = ARGV[3]
local error_msg = ARGV[4]
local timestamp_str = ARGV[5]
local retry_delay_score = tonumber(ARGV[6])
local timestamp_ms = tonumber(ARGV[7])

local current_lease = redis.call("GET", lease_key)
if current_lease ~= lease_id then
    return "error: lease_mismatch"
end

local raw_data = redis.call("HGET", task_key, "data")
if not raw_data then return "error: task_not_found" end
pcall(cjson.encode_empty_table_as_object, true)
local task_data = cjson.decode(raw_data)

local from_status = task_data.status
if task_data.attempt < task_data.max_retries then
    task_data.status = "RETRYING"
    redis.call("ZADD", retry_queue_key, retry_delay_score, task_id)
else
    task_data.status = "FAILED"
    redis.call("LPUSH", dlq_key, task_id)
    redis.call("INCR", metrics_failed)
end

if task_data.started_at_ms and timestamp_ms then
    task_data.execution_duration_ms = timestamp_ms - task_data.started_at_ms
end

task_data.error = error_msg
table.insert(task_data.retry_history, {
    attempt = task_data.attempt,
    error = error_msg,
    timestamp = timestamp_str,
    worker_id = worker_id
})

table.insert(task_data.state_history, {
    from_status = from_status,
    to_status = task_data.status,
    timestamp = timestamp_str,
    worker_id = worker_id,
    reason = "failed"
})

redis.call("HSET", task_key, "data", cjson.encode(task_data))
redis.call("SREM", active_tasks_key, task_id)
redis.call("SREM", worker_tasks_key, task_id)
redis.call("DEL", lease_key)

local event_type = "TASK_FAILED"
if task_data.status == "RETRYING" then
    event_type = "TASK_RETRYING"
end
local event = cjson.encode({
    event_type = event_type,
    timestamp = timestamp_str,
    task_id = task_id,
    worker_id = worker_id,
    details = { error = error_msg, attempt = task_data.attempt }
})
redis.call("PUBLISH", events_channel, event)

return task_data.status
