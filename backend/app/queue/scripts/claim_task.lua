-- keys: priority_queue_key, active_tasks_key, worker_tasks_key, events_channel
-- args: worker_id, lease_id, lease_duration, timestamp

local priority_queue_key = KEYS[1]
local active_tasks_key = KEYS[2]
local worker_tasks_key = KEYS[3]
local events_channel = KEYS[4]

local worker_id = ARGV[1]
local lease_id = ARGV[2]
local lease_duration = tonumber(ARGV[3])
local timestamp = tonumber(ARGV[4])
local timestamp_str = ARGV[5]

local item = redis.call("ZPOPMIN", priority_queue_key)
if not item or #item == 0 then
    return nil
end

local task_id = item[1]
local task_hash_key = "ts:task:" .. task_id

local raw_data = redis.call("HGET", task_hash_key, "data")
if not raw_data then
    return nil
end
pcall(cjson.encode_empty_table_as_object, true)
local task_data = cjson.decode(raw_data)

task_data.status = "RUNNING"
task_data.worker_id = worker_id
task_data.lease_id = lease_id
task_data.started_at = timestamp_str
task_data.attempt = task_data.attempt + 1
task_data.started_at_ms = timestamp * 1000

local state_transition = {
    from_status = "QUEUED",
    to_status = "RUNNING",
    timestamp = task_data.started_at,
    worker_id = worker_id,
    reason = "claimed"
}
table.insert(task_data.state_history, state_transition)

redis.call("HSET", task_hash_key, "data", cjson.encode(task_data))
redis.call("SADD", active_tasks_key, task_id)
redis.call("SADD", worker_tasks_key, task_id)

local lease_key = "ts:lease:" .. task_id
redis.call("SET", lease_key, lease_id, "EX", lease_duration)

local event = cjson.encode({
    event_type = "TASK_STARTED",
    timestamp = timestamp_str,
    task_id = task_id,
    worker_id = worker_id,
    details = {}
})
redis.call("PUBLISH", events_channel, event)

return cjson.encode(task_data)
