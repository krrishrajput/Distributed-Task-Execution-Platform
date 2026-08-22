-- keys: scheduled_queue, priority_queue, sequence_key
-- args: current_timestamp
local scheduled_queue = KEYS[1]
local p_queue = KEYS[2]
local sequence_key = KEYS[3]
local current_time = tonumber(ARGV[1])

local items = redis.call("ZRANGEBYSCORE", scheduled_queue, "-inf", current_time)
if #items == 0 then return 0 end

for _, tid in ipairs(items) do
    local raw_data = redis.call("HGET", "ts:task:" .. tid, "data")
    if raw_data then
        pcall(cjson.encode_empty_table_as_object, true)
        local task_data = cjson.decode(raw_data)
        task_data.status = "QUEUED"
        redis.call("HSET", "ts:task:" .. tid, "data", cjson.encode(task_data))
        
        local seq = redis.call("INCR", sequence_key)
        local score = (task_data.priority * 100000000000000) + seq
        redis.call("ZADD", p_queue, tostring(score), tid)
    end
end
redis.call("ZREMRANGEBYSCORE", scheduled_queue, "-inf", current_time)
return #items
