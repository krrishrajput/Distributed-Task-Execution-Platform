-- KEYS: lease_key
-- ARGS: lease_id, lease_duration
local lease_key = KEYS[1]
local lease_id = ARGV[1]
local lease_duration = tonumber(ARGV[2])

local current_lease = redis.call("GET", lease_key)
if current_lease == lease_id then
    redis.call("EXPIRE", lease_key, lease_duration)
    return "ok"
end
return "error: lease_mismatch"
