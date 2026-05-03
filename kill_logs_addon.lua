-- GAR Bot - Kill Logs Addon
local BOT_URL    = "https://discord-bot2-production-1653.up.railway.app/log"
local AUTH_TOKEN = "Danulite2009"
local SERVER_NAME = "SCP: Roleplay"

local function urlEncode(str)
    str = tostring(str)
    str = str:gsub("([^%w%-%.%_%~ ])", function(c)
        return string.format("%%%02X", string.byte(c))
    end)
    return str:gsub(" ", "+")
end

local function sendKill(killer, victim)
    local url = BOT_URL
        .. "?token=" .. AUTH_TOKEN
        .. "&type=kill"
        .. "&player=" .. urlEncode(killer)
        .. "&victim=" .. urlEncode(victim)
        .. "&server=" .. urlEncode(SERVER_NAME)

    local ok, err = pcall(http, url)
    if not ok then
        warn("[GARBot] Kill log failed: " .. tostring(err))
    end
end

event("playerRespawned", function(data)
    local victim = tostring(data.Value[1])
    local killer = tostring(data.Value[2] or "Unknown")
    task.spawn(sendKill, killer, victim)
end)

print("[GARBot] Kill logs addon loaded")
