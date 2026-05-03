-- SCP:RP Jail System
-- Allowed teams: Coruscant Guards, Republic Intelligence, Galactic Council, Officer Corps
-- Logs jail/unjail actions to Discord via GAR Bot

local HttpService  = game:GetService("HttpService")
local Players      = game:GetService("Players")

local BOT_URL      = "discord-bot2-production-1653.up.railway.app"  -- Replace with your Railway URL
local AUTH_TOKEN   = "Danulite2009"      -- Must match ROBLOX_AUTH_TOKEN in Railway
local SERVER_NAME  = "SCP: Roleplay - Private Server"

local ALLOWED_TEAMS = {
	["Coruscant Guards"]    = true,
	["Republic Intelligence"] = true,
	["Galactic Council"]    = true,
	["Officer Corps"]       = true,
}

local jailedPlayers = {} -- [playerName] = {reason="", remaining=0}

-- ── Helpers ────────────────────────────────────────────────────────────────────
local function getTeam(playerName)
	local player = Players:FindFirstChild(playerName)
	if player and player.Team then
		return player.Team.Name
	end
	return nil
end

local function isAllowed(playerName)
	local team = getTeam(playerName)
	return team and ALLOWED_TEAMS[team] == true, team
end

local function sendLog(data)
	local ok, err = pcall(function()
		HttpService:PostAsync(
			BOT_URL,
			HttpService:JSONEncode(data),
			Enum.HttpContentType.ApplicationJson,
			false,
			{ Authorization = "Bearer " .. AUTH_TOKEN }
		)
	end)
	if not ok then
		warn("[GARBot] Failed to send jail log: " .. tostring(err))
	end
end

-- ── Timer updater ──────────────────────────────────────────────────────────────
local function updateTimers()
	while true do
		for playerName, info in pairs(jailedPlayers) do
			info.remaining = info.remaining - 1

			if info.remaining <= 0 then
				runCommand(":team " .. playerName .. " players")
				runCommand(":unpermntag " .. playerName)
				runCommand(":unpermrtag " .. playerName)
				runCommand(":kill " .. playerName)
				runCommand(":res " .. playerName)
				jailedPlayers[playerName] = nil
				runCommand(":pm " .. playerName .. " You've been released from jail!")

				-- Log auto-release to Discord
				task.spawn(sendLog, {
					type          = "unjail",
					target        = playerName,
					executor      = "System (timer expired)",
					executor_team = "Automatic",
					server        = SERVER_NAME,
				})
			else
				runCommand(":permntag " .. playerName .. "[" .. info.remaining .. "]")
				runCommand(":permrtag " .. playerName .. "[" .. info.reason .. "]")
			end
		end
		task.wait(1)
	end
end

task.spawn(updateTimers)

-- ── Persist tags on respawn ────────────────────────────────────────────────────
event("playerRespawned", function(playerName)
	local info = jailedPlayers[playerName]
	if info then
		runCommand(":team " .. playerName .. " jail")
		runCommand(":permntag " .. playerName .. "[" .. info.remaining .. "]")
		runCommand(":permrtag " .. playerName .. "[" .. info.reason .. "]")
	end
end)

-- ── Chat listener ──────────────────────────────────────────────────────────────
event("chatted", function(data)
	local executor = data.Value[1]
	local message  = tostring(data.Value[2])

	local words = {}
	for word in message:gmatch("%S+") do table.insert(words, word) end

	-- :jail <player> <reason> <time>
	if words[1] == ":jail" and words[2] and words[3] and words[4] then
		local allowed, executorTeam = isAllowed(executor)
		if not allowed then
			runCommand(":pm " .. executor .. " You are not authorized to use :jail. Allowed teams: Coruscant Guards, Republic Intelligence, Galactic Council, Officer Corps.")
			return
		end

		local target  = words[2]
		local reason  = words[3]
		local timeSec = tonumber(words[4])

		if not timeSec or timeSec <= 0 then
			runCommand(":pm " .. executor .. " Invalid jail time.")
			return
		end

		jailedPlayers[target] = {reason = reason, remaining = timeSec}
		runCommand(":team " .. target .. " jail")
		runCommand(":permntag " .. target .. "[" .. timeSec .. "]")
		runCommand(":permrtag " .. target .. "[" .. reason .. "]")
		runCommand(":kill " .. target)
		runCommand(":res " .. target)
		runCommand(":pm " .. target .. " You have been jailed for " .. timeSec .. " seconds! Reason: " .. reason)
		runCommand(":pm " .. executor .. " " .. target .. " has been jailed for " .. timeSec .. " seconds! Reason: " .. reason)

		-- Log to Discord
		task.spawn(sendLog, {
			type          = "jail",
			target        = target,
			executor      = executor,
			executor_team = executorTeam or "Unknown",
			reason        = reason,
			duration      = timeSec,
			server        = SERVER_NAME,
		})

	-- :unjail <player>
	elseif words[1] == ":unjail" and words[2] then
		local allowed, executorTeam = isAllowed(executor)
		if not allowed then
			runCommand(":pm " .. executor .. " You are not authorized to use :unjail. Allowed teams: Coruscant Guards, Republic Intelligence, Galactic Council, Officer Corps.")
			return
		end

		local target = words[2]
		if jailedPlayers[target] then
			jailedPlayers[target] = nil
			runCommand(":team " .. target .. " players")
			runCommand(":unpermntag " .. target)
			runCommand(":unpermrtag " .. target)
			runCommand(":kill " .. target)
			runCommand(":res " .. target)
			runCommand(":pm " .. target .. " You have been bailed by " .. executor .. "!")
			runCommand(":pm " .. executor .. " " .. target .. " has been released early.")

			-- Log to Discord
			task.spawn(sendLog, {
				type          = "unjail",
				target        = target,
				executor      = executor,
				executor_team = executorTeam or "Unknown",
				server        = SERVER_NAME,
			})
		else
			runCommand(":pm " .. executor .. " " .. target .. " is not jailed.")
		end
	end
end)
