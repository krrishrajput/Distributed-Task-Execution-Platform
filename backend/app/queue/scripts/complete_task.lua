-- keys: task_key, lease_key, active_tasks_key, worker_tasks_key, metrics_completed_key, events_channel
-- args: task_id, worker_id, lease_id, result_json, timestamp_str, timestamp_ms
local task_key = KEYS[1]
local lease_key = KEYS[2]
local active_tasks_key = KEYS[3]
local worker_tasks_key = KEYS[4]
local metrics_completed_key = KEYS[5]
local events_channel = KEYS[6]

local task_id = ARGV[1]
local worker_id = ARGV[2]
local lease_id = ARGV[3]
local result_json = ARGV[4]
local timestamp_str = ARGV[5]
local timestamp_ms = tonumber(ARGV[6])

local current_lease = redis.call("GET", lease_key)
if current_lease ~= lease_id then
    return "error: lease_mismatch"
end

local raw_data = redis.call("HGET", task_key, "data")
if not raw_data then return "error: task_not_found" end
pcall(cjson.encode_empty_table_as_object, true)
local task_data = cjson.decode(raw_data)

task_data.status = "COMPLETED"
task_data.completed_at = timestamp_str
if result_json ~= "" then task_data.result = cjson.decode(result_json) end

if task_data.started_at_ms and timestamp_ms then
    task_data.execution_duration_ms = timestamp_ms - task_data.started_at_ms
end

table.insert(task_data.state_history, {
    from_status = "RUNNING",
    to_status = "COMPLETED",
    timestamp = timestamp_str,
    worker_id = worker_id,
    reason = "completed"
})

redis.call("HSET", task_key, "data", cjson.encode(task_data))
redis.call("SREM", active_tasks_key, task_id)
redis.call("SREM", worker_tasks_key, task_id)
redis.call("DEL", lease_key)
redis.call("INCR", metrics_completed_key)

local event = cjson.encode({
    event_type = "TASK_COMPLETED",
    timestamp = timestamp_str,
    task_id = task_id,
    worker_id = worker_id,
    details = {}
})
redis.call("PUBLISH", events_channel, event)

return "ok"
