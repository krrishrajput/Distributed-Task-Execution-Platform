-- keys: task_hash_key, priority_queue_key, scheduled_queue_key, idempotency_key_key, metrics_submitted_key, events_channel
-- args: task_id, task_json_data, score, scheduled_at_score, idempotency_key, event_json, idempotency_ttl

local task_hash_key = KEYS[1]
local priority_queue_key = KEYS[2]
local scheduled_queue_key = KEYS[3]
local idempotency_key_key = KEYS[4]
local metrics_submitted_key = KEYS[5]
local events_channel = KEYS[6]

local task_id = ARGV[1]
local task_json_data = ARGV[2]
local score = tonumber(ARGV[3])
local scheduled_at_score = tonumber(ARGV[4])
local idempotency_key = ARGV[5]
local event_json = ARGV[6]
local idempotency_ttl = tonumber(ARGV[7])

if idempotency_key ~= "" then
    local set_result = redis.call("SET", idempotency_key_key, task_id, "NX", "EX", idempotency_ttl)
    if not set_result then
        local existing_task_id = redis.call("GET", idempotency_key_key)
        return {existing_task_id, "duplicate"}
    end
end

redis.call("HSET", task_hash_key, "data", task_json_data)
if scheduled_at_score > 0 then
    redis.call("ZADD", scheduled_queue_key, scheduled_at_score, task_id)
else
    redis.call("ZADD", priority_queue_key, score, task_id)
end

redis.call("INCR", metrics_submitted_key)
if event_json ~= "" then
    redis.call("PUBLISH", events_channel, event_json)
end

return {task_id, "enqueued"}
