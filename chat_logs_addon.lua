-- GAR Bot - Chat Logs Addon
local BOT_URL   = "https://discord-bot2-production-1653.up.railway.app/log"
local AUTH_TOKEN = "Danulite2009"
local SERVER_NAME = "SCP: Roleplay"

local function urlEncode(str)
    str = tostring(str)
    str = str:gsub("([^%w%-%.%_%~ ])", function(c)
        return string.format("%%%02X", string.byte(c))
    end)
    return str:gsub(" ", "+")
end

local function sendChat(playerName, message)
    local url = BOT_URL
        .. "?token=" .. AUTH_TOKEN
        .. "&type=chat"
        .. "&player=" .. urlEncode(playerName)
        .. "&message=" .. urlEncode(message)
        .. "&server=" .. urlEncode(SERVER_NAME)

    local ok, err = pcall(http, url)
    if not ok then
        warn("[GARBot] Chat log failed: " .. tostring(err))
    end
end

event("chatted", function(data)
    task.spawn(sendChat, tostring(data.Value[1]), tostring(data.Value[2]))
end)

print("[GARBot] Chat logs addon loaded")
