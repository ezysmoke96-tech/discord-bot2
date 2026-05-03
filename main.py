import os
import asyncio
import threading
import datetime
import discord
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask, request, jsonify

load_dotenv()

TOKEN = os.environ.get("DISCORD_TOKEN")
ROBLOX_AUTH_TOKEN = os.environ.get("ROBLOX_AUTH_TOKEN", "changeme")

KILL_LOG_CHANNEL_ID = 1500538920075530251
CHAT_LOG_CHANNEL_ID = 1500538964518637678
JAIL_LOG_CHANNEL_ID = 1500543345922146335

COGS = [
    "cogs.general",
    "cogs.moderation",
    "cogs.logging_cog",
    "cogs.welcome",
    "cogs.verification",
    "cogs.roblox_info",
    "cogs.debug",
    "cogs.antiraid",
    "cogs.warnings",
    "cogs.giveaway",
]

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# ── Web server ─────────────────────────────────────────────────────────────────
web = Flask(__name__)
_loop: asyncio.AbstractEventLoop | None = None


@web.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@web.route("/log", methods=["POST"])
def receive_log():
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {ROBLOX_AUTH_TOKEN}":
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    log_type = data.get("type")
    if log_type == "kill":
        asyncio.run_coroutine_threadsafe(_post_kill(data), _loop)
    elif log_type == "chat":
        asyncio.run_coroutine_threadsafe(_post_chat(data), _loop)
    elif log_type == "jail":
        asyncio.run_coroutine_threadsafe(_post_jail(data), _loop)
    elif log_type == "unjail":
        asyncio.run_coroutine_threadsafe(_post_unjail(data), _loop)
    else:
        return jsonify({"error": f"Unknown log type: {log_type}"}), 400

    return jsonify({"ok": True}), 200


async def _post_kill(data: dict):
    channel = bot.get_channel(KILL_LOG_CHANNEL_ID)
    if not channel:
        print(f"[roblox] Kill log channel {KILL_LOG_CHANNEL_ID} not found")
        return
    embed = discord.Embed(
        title="⚔️ Kill Log",
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow(),
    )
    embed.add_field(name="Killer", value=data.get("killer", "Unknown"), inline=True)
    embed.add_field(name="Victim", value=data.get("victim", "Unknown"), inline=True)
    if data.get("weapon"):
        embed.add_field(name="Weapon", value=data["weapon"], inline=True)
    embed.set_footer(text=f"SCP: Roleplay • {data.get('server', 'Private Server')}")
    await channel.send(embed=embed)


async def _post_chat(data: dict):
    channel = bot.get_channel(CHAT_LOG_CHANNEL_ID)
    if not channel:
        print(f"[roblox] Chat log channel {CHAT_LOG_CHANNEL_ID} not found")
        return
    player = data.get("player", "Unknown")
    message = data.get("message", "")
    if len(message) > 1000:
        message = message[:997] + "..."
    embed = discord.Embed(
        description=f"**{player}:** {message}",
        color=discord.Color.blurple(),
        timestamp=datetime.datetime.utcnow(),
    )
    embed.set_footer(text=f"SCP: Roleplay • {data.get('server', 'Private Server')}")
    await channel.send(embed=embed)


async def _post_jail(data: dict):
    if not JAIL_LOG_CHANNEL_ID:
        print("[roblox] JAIL_LOG_CHANNEL_ID not set")
        return
    channel = bot.get_channel(JAIL_LOG_CHANNEL_ID)
    if not channel:
        print(f"[roblox] Jail log channel {JAIL_LOG_CHANNEL_ID} not found")
        return
    embed = discord.Embed(
        title="🔒 Player Jailed",
        color=discord.Color.orange(),
        timestamp=datetime.datetime.utcnow(),
    )
    embed.add_field(name="Player", value=data.get("target", "Unknown"), inline=True)
    embed.add_field(name="Jailed By", value=data.get("executor", "Unknown"), inline=True)
    embed.add_field(name="Team", value=data.get("executor_team", "Unknown"), inline=True)
    embed.add_field(name="Reason", value=data.get("reason", "No reason"), inline=True)
    embed.add_field(name="Duration", value=f"{data.get('duration', 0)} seconds", inline=True)
    embed.set_footer(text=f"SCP: Roleplay • {data.get('server', 'Private Server')}")
    await channel.send(embed=embed)


async def _post_unjail(data: dict):
    if not JAIL_LOG_CHANNEL_ID:
        print("[roblox] JAIL_LOG_CHANNEL_ID not set")
        return
    channel = bot.get_channel(JAIL_LOG_CHANNEL_ID)
    if not channel:
        print(f"[roblox] Jail log channel {JAIL_LOG_CHANNEL_ID} not found")
        return
    embed = discord.Embed(
        title="🔓 Player Released",
        color=discord.Color.green(),
        timestamp=datetime.datetime.utcnow(),
    )
    embed.add_field(name="Player", value=data.get("target", "Unknown"), inline=True)
    embed.add_field(name="Released By", value=data.get("executor", "Unknown"), inline=True)
    embed.add_field(name="Team", value=data.get("executor_team", "Unknown"), inline=True)
    embed.set_footer(text=f"SCP: Roleplay • {data.get('server', 'Private Server')}")
    await channel.send(embed=embed)


# ── Bot events ─────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)


# ── Entry point ────────────────────────────────────────────────────────────────
async def main():
    global _loop
    _loop = asyncio.get_running_loop()

    port = int(os.environ.get("PORT", 8080))
    flask_thread = threading.Thread(
        target=lambda: web.run(host="0.0.0.0", port=port, use_reloader=False),
        daemon=True,
    )
    flask_thread.start()
    print(f"[web] Listening on port {port}")

    async with bot:
        for cog in COGS:
            await bot.load_extension(cog)
        await bot.start(TOKEN)


if __name__ == "__main__":
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN secret is not set.")
    asyncio.run(main())
