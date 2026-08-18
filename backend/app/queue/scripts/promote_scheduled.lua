-- keys: scheduled_queue_key, priority_queue_key
-- args: current_time_score, limit
local scheduled = KEYS[1]
local priority = KEYS[2]
local current_time = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])

local items = redis.call("ZRANGEBYSCORE", scheduled, "-inf", current_time, "LIMIT", 0, limit)
local promoted = 0

for _, task_id in ipairs(items) do
    local task_key = "ts:task:" .. task_id
    local raw_data = redis.call("HGET", task_key, "data")
    if raw_data then
        local task_data = cjson.decode(raw_data)
        redis.call("ZADD", priority, task_data.priority, task_id)
        
        task_data.status = "QUEUED"
        redis.call("HSET", task_key, "data", cjson.encode(task_data))
        promoted = promoted + 1
    end
    redis.call("ZREM", scheduled, task_id)
end

return promoted
