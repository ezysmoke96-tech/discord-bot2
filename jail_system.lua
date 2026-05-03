-- GAR Bot - Jail System Addon
local BOT_URL     = "https://discord-bot2-production-1653.up.railway.app/log"
local AUTH_TOKEN  = "Danulite2009"
local SERVER_NAME = "SCP: Roleplay"

local ALLOWED_TEAMS = {
    ["Coruscant Guards"]      = true,
    ["Republic Intelligence"] = true,
    ["Galactic Council"]      = true,
    ["Officer Corps"]         = true,
}

local function urlEncode(str)
    str = tostring(str)
    local result = ""
    for i = 1, #str do
        local c = str:sub(i, i)
        local b = string.byte(c)
        if (b >= 65 and b <= 90) or (b >= 97 and b <= 122) or
           (b >= 48 and b <= 57) or c == "-" or c == "_" or c == "." then
            result = result .. c
        else
            result = result .. string.format("%%%02X", b)
        end
    end
    return result
end

local function sendLog(logType, officer, target, reason, duration)
    local url = BOT_URL
        .. "?token=" .. AUTH_TOKEN
        .. "&type="   .. logType
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
    if not ok then warn("[GARBot] Jail log failed: " .. tostring(err)) end
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
    local officer = tostring(player)

    local team = getTeam(player)
    if not team or not ALLOWED_TEAMS[team] then return end

    -- :jail <user> <reason> <time>
    -- reason can have spaces; time is always the last word
    local target, rest = message:match("^:jail%s+(%S+)%s+(.+)$")
    if target and rest then
        local reason, duration = rest:match("^(.+)%s+(%S+)$")
        if not reason then
            reason   = rest
            duration = "N/A"
        end

        -- Run in-game commands
        runCommand(":rtag " .. target .. " " .. reason)
        runCommand(":ntag " .. target .. " " .. duration)
        runCommand(":team " .. target .. " Jail")
        runCommand(":res "  .. target)

        task.spawn(sendLog, "jail", officer, target, reason, duration)
        return
    end

    -- :unjail <user>
    local unjailTarget = message:match("^:unjail%s+(%S+)$")
    if unjailTarget then
        runCommand(":unteam " .. unjailTarget)
        runCommand(":res "    .. unjailTarget)

        task.spawn(sendLog, "unjail", officer, unjailTarget, nil, nil)
        return
    end
end)

print("[GARBot] Jail system addon loaded")
