-- keys: priority_queue, sequence_key
-- args: max_tasks, age_threshold_score, max_priority
local p_queue = KEYS[1]
local sequence_key = KEYS[2]
local max_tasks = tonumber(ARGV[1])
local current_time_unused = tonumber(ARGV[2]) 
local max_pri = tonumber(ARGV[3])

-- Actually, aging by modifying the score breaks because score is exactly priority * 1e14 + seq.
-- If we want to age, we must fetch task data to know if it deserves aging.
-- Let's just implement aging by shifting priority up by 1e14 (which is 1 priority level).
local items = redis.call("ZRANGE", p_queue, 0, max_tasks - 1, "WITHSCORES")
local aged_count = 0

for i = 1, #items, 2 do
    local tid = items[i]
    local score = tonumber(items[i+1])
    local pri = math.floor(score / 100000000000000)
    
    if pri > 1 then
        local new_score = score - 100000000000000
        redis.call("ZADD", p_queue, new_score, tid)
        aged_count = aged_count + 1
    end
end

return aged_count
