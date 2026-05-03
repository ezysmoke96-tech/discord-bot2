-- GAR Bot - Kill Logs Addon
local BOT_URL     = "https://discord-bot2-production-1653.up.railway.app/log"
local AUTH_TOKEN  = "Danulite2009"
local SERVER_NAME = "SCP: Roleplay"

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

event("playerRespawned", function(data)
    if not data then return end
    if not data.Value then return end
    if not data.Value[1] then return end
    if not data.Value[2] then return end

    local victim = tostring(data.Value[1])
    local killer = tostring(data.Value[2])
    local weapon = data.Value[3] and tostring(data.Value[3]) or "Unknown"

    local url = BOT_URL
        .. "?token=" .. AUTH_TOKEN
        .. "&type=kill"
        .. "&player=" .. urlEncode(killer)
        .. "&victim=" .. urlEncode(victim)
        .. "&weapon=" .. urlEncode(weapon)
        .. "&server=" .. urlEncode(SERVER_NAME)

    print("[GARBot] URL:", url)
    local ok, result = pcall(http, url)
    if not ok then warn("[GARBot] Error:", tostring(result)) end
end)

print("[GARBot] Kill logs addon loaded")
