-- GAR Bot - Jail System Addon
local BOT_URL    = "https://discord-bot2-production-1653.up.railway.app/log"
local AUTH_TOKEN = "Danulite2009"
local SERVER_NAME = "SCP: Roleplay"

local ALLOWED_TEAMS = {
    ["Coruscant Guards"]     = true,
    ["Republic Intelligence"] = true,
    ["Galactic Council"]     = true,
    ["Officer Corps"]        = true,
}

local function urlEncode(str)
    str = tostring(str)
    str = str:gsub("([^%w%-%.%_%~ ])", function(c)
        return string.format("%%%02X", string.byte(c))
    end)
    return str:gsub(" ", "+")
end

local function sendLog(logType, officer, target, reason, duration)
    local url = BOT_URL
        .. "?token=" .. AUTH_TOKEN
        .. "&type=" .. logType
        .. "&player=" .. urlEncode(officer)
        .. "&target=" .. urlEncode(target)
        .. "&server=" .. urlEncode(SERVER_NAME)

    if reason then
        url = url .. "&reason=" .. urlEncode(reason)
    end
    if duration then
        url = url .. "&duration=" .. urlEncode(tostring(duration))
    end

    local ok, err = pcall(http, url)
    if not ok then
        warn("[GARBot] Jail log failed: " .. tostring(err))
    end
end

local function getTeam(player)
    if player and player.Team then
        return player.Team.Name
    end
    return nil
end

event("chatted", function(data)
    local player  = data.Value[1]
    local message = tostring(data.Value[2])

    local team = getTeam(player)
    if not team or not ALLOWED_TEAMS[team] then return end

    -- !jail <target> <duration> <reason>
    local target, duration, reason = message:match("^!jail%s+(%S+)%s+(%S+)%s+(.+)$")
    if target and duration and reason then
        task.spawn(sendLog, "jail", tostring(player), target, reason, duration)
        return
    end

    -- !unjail <target>
    local unjailTarget = message:match("^!unjail%s+(%S+)$")
    if unjailTarget then
        task.spawn(sendLog, "unjail", tostring(player), unjailTarget, nil, nil)
        return
    end
end)

print("[GARBot] Jail system addon loaded")
