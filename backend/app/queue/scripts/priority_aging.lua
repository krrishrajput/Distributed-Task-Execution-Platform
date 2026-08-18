-- keys: priority_queue_key
-- args: aging_amount, max_items
local priority_queue_key = KEYS[1]
local aging_amount = tonumber(ARGV[1]) or 1
local max_items = tonumber(ARGV[2]) or 100

local items = redis.call("ZRANGE", priority_queue_key, 0, max_items - 1, "WITHSCORES")
local aged = 0

for i = 1, #items, 2 do
    local task_id = items[i]
    local current_score = tonumber(items[i+1])
    
    -- Extract priority component (score / 1e12)
    local pri = math.floor(current_score / 1000000000000)
    if pri > 1 then
        local new_pri = pri - aging_amount
        if new_pri < 1 then new_pri = 1 end
        
        local remainder = current_score - (pri * 1000000000000)
        local new_score = (new_pri * 1000000000000) + remainder
        
        redis.call("ZADD", priority_queue_key, new_score, task_id)
        aged = aged + 1
    end
end

return aged
