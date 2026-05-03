-- GAR Bot - Roblox Server Addon
-- Paste this script into your SCP: Roleplay private server addon
-- Replace BOT_URL and AUTH_TOKEN with your actual values

local HttpService = game:GetService("HttpService")
local Players = game:GetService("Players")

local BOT_URL = "discord-bot2-production-1653.up.railway.app"  -- Replace with your Railway URL
local AUTH_TOKEN = "Danulite2009"  -- Must match ROBLOX_AUTH_TOKEN in Railway
local SERVER_NAME = "SCP: Roleplay - Private Server"

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
		warn("[GARBot] Failed to send log: " .. tostring(err))
	end
end

-- ── Chat Logs ──────────────────────────────────────────────────────────────────
Players.PlayerAdded:Connect(function(player)
	player.Chatted:Connect(function(message)
		sendLog({
			type = "chat",
			player = player.Name,
			message = message,
			server = SERVER_NAME,
		})
	end)
end)

-- ── Kill Logs ──────────────────────────────────────────────────────────────────
-- Hook into character deaths to detect kills
Players.PlayerAdded:Connect(function(player)
	player.CharacterAdded:Connect(function(character)
		local humanoid = character:WaitForChild("Humanoid")

		humanoid.Died:Connect(function()
			local killer = nil
			local tag = humanoid:FindFirstChild("creator")
			if tag and tag:IsA("ObjectValue") and tag.Value then
				killer = tag.Value.Name
			end

			sendLog({
				type = "kill",
				killer = killer or "Unknown / Environment",
				victim = player.Name,
				server = SERVER_NAME,
			})
		end)
	end)
end)

print("[GARBot] Roblox addon loaded successfully")
