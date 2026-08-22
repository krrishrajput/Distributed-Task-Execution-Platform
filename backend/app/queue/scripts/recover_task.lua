-- keys: task_key, lease_key, priority_queue_key, active_tasks_key, worker_tasks_key, events_channel, sequence_key
-- args: task_id, timestamp_str
local task_key = KEYS[1]
local lease_key = KEYS[2]
local priority_queue_key = KEYS[3]
local active_tasks_key = KEYS[4]
local worker_prefix = KEYS[5]
local events_channel = KEYS[6]
local sequence_key = KEYS[7]

local task_id = ARGV[1]
local timestamp_str = ARGV[2]

local raw_data = redis.call("HGET", task_key, "data")
if not raw_data then return "error: task_not_found" end

pcall(cjson.encode_empty_table_as_object, true)
local task_data = cjson.decode(raw_data)

if task_data.status ~= "RUNNING" then
    -- Already completed or failed, safely ignore
    return "ignored: not_running"
end

local from_status = task_data.status
task_data.status = "QUEUED"
task_data.updated_at = timestamp_str

local old_worker = task_data.worker_id

table.insert(task_data.state_history, {
    from_status = from_status,
    to_status = "QUEUED",
    timestamp = timestamp_str,
    reason = "worker_recovery"
})

redis.call("HSET", task_key, "data", cjson.encode(task_data))
redis.call("SREM", active_tasks_key, task_id)
if old_worker then
    redis.call("SREM", worker_prefix .. ":" .. old_worker .. ":tasks", task_id)
end
redis.call("DEL", lease_key)

redis.call("INCR", "ts:metrics:recovered")
local seq = redis.call("INCR", sequence_key)
local score = (task_data.priority * 100000000000000) + seq
redis.call("ZADD", priority_queue_key, tostring(score), task_id)

local event = cjson.encode({
    event_type = "TASK_RECOVERED",
    timestamp = timestamp_str,
    task_id = task_id,
    details = {}
})
redis.call("PUBLISH", events_channel, event)

return "ok"
