-- keys: task_key, lease_key, priority_queue_key, active_tasks_key, worker_tasks_key, events_channel
-- args: task_id, timestamp_str
local task_key = KEYS[1]
local lease_key = KEYS[2]
local priority_queue_key = KEYS[3]
local active_tasks_key = KEYS[4]
local worker_tasks_key = KEYS[5]
local events_channel = KEYS[6]

local task_id = ARGV[1]
local timestamp_str = ARGV[2]

local raw_data = redis.call("HGET", task_key, "data")
if not raw_data then return "error: task_not_found" end
local task_data = cjson.decode(raw_data)

if task_data.status ~= "RUNNING" then
    return "error: not_running"
end

local current_lease = redis.call("GET", lease_key)
if current_lease then
    return "error: lease_active"
end

local old_worker = task_data.worker_id
task_data.status = "QUEUED"
task_data.worker_id = cjson.null
task_data.lease_id = cjson.null

table.insert(task_data.state_history, {
    from_status = "RUNNING",
    to_status = "QUEUED",
    timestamp = timestamp_str,
    worker_id = old_worker,
    reason = "recovered"
})

redis.call("HSET", task_key, "data", cjson.encode(task_data))
redis.call("ZADD", priority_queue_key, task_data.priority, task_id)
redis.call("SREM", active_tasks_key, task_id)
if old_worker and old_worker ~= cjson.null then
    redis.call("SREM", worker_tasks_key .. ":" .. old_worker, task_id)
end

return "ok"
