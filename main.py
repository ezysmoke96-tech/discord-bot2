import discord
from discord.ext import commands
import os
import threading
import datetime
from flask import Flask, request, jsonify

# ── Flask web server ──────────────────────────────────────────────────────────
app = Flask(__name__)

AUTH_TOKEN = os.environ.get("ROBLOX_AUTH_TOKEN", "Danulite2009")

KILL_CHANNEL_ID = 1500538920075530251
CHAT_CHANNEL_ID = 1500538964518637678
JAIL_CHANNEL_ID = 1500543345922146335

bot_ref = None  # set after bot is created

def get_embed(log_type, params):
    player  = params.get("player", "Unknown")
    server  = params.get("server", "Unknown")
    message = params.get("message", "")
    target  = params.get("target", "")
    reason  = params.get("reason", "")
    duration = params.get("duration", "")

    if log_type == "chat":
        embed = discord.Embed(title="💬 Chat Log", color=0x3498db)
        embed.add_field(name="Player",   value=player,  inline=True)
        embed.add_field(name="Message",  value=message, inline=False)
        embed.add_field(name="Server",   value=server,  inline=False)
        return embed, CHAT_CHANNEL_ID

    elif log_type == "kill":
        victim = params.get("victim", "Unknown")
        weapon = params.get("weapon", "Unknown")
        now    = datetime.datetime.utcnow().strftime("%m/%d")
        embed  = discord.Embed(title="💀 Kill Log", color=0xe74c3c)
        embed.add_field(name="Killer", value=player, inline=False)
        embed.add_field(name="Victim", value=victim, inline=False)
        embed.add_field(name="Time",   value=now,    inline=False)
        embed.add_field(name="Weapon", value=weapon, inline=False)
        return embed, KILL_CHANNEL_ID

    elif log_type == "jail":
        embed = discord.Embed(title="🔒 Arrested", color=0xe67e22)
        embed.add_field(name="Arrested By", value=player,          inline=False)
        embed.add_field(name="Player",      value=target or "N/A", inline=False)
        embed.add_field(name="Time",        value=duration or "N/A", inline=False)
        embed.add_field(name="Reason",      value=reason or "N/A", inline=False)
        embed.add_field(name="Server",      value=server,          inline=False)
        return embed, JAIL_CHANNEL_ID

    elif log_type == "unjail":
        embed = discord.Embed(title="🔓 Released", color=0x2ecc71)
        embed.add_field(name="Released By", value=player,          inline=False)
        embed.add_field(name="Player",      value=target or "N/A", inline=False)
        embed.add_field(name="Server",      value=server,          inline=False)
        return embed, JAIL_CHANNEL_ID

    return None, None


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/log")
def log_get():
    token = request.args.get("token", "")
    if token != AUTH_TOKEN:
        return jsonify({"error": "unauthorized"}), 401

    log_type = request.args.get("type", "")
    params   = request.args.to_dict()

    embed, channel_id = get_embed(log_type, params)
    if embed is None:
        return jsonify({"error": "unknown log type"}), 400

    if bot_ref is None:
        return jsonify({"error": "bot not ready"}), 503

    async def send():
        ch = bot_ref.get_channel(channel_id)
        if ch:
            await ch.send(embed=embed)

    import asyncio
    asyncio.run_coroutine_threadsafe(send(), bot_ref.loop)
    return jsonify({"status": "logged"})


@app.route("/log", methods=["POST"])
def log_post():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if token != AUTH_TOKEN:
        return jsonify({"error": "unauthorized"}), 401

    data     = request.get_json(force=True) or {}
    log_type = data.get("type", "")

    embed, channel_id = get_embed(log_type, data)
    if embed is None:
        return jsonify({"error": "unknown log type"}), 400

    if bot_ref is None:
        return jsonify({"error": "bot not ready"}), 503

    async def send():
        ch = bot_ref.get_channel(channel_id)
        if ch:
            await ch.send(embed=embed)

    import asyncio
    asyncio.run_coroutine_threadsafe(send(), bot_ref.loop)
    return jsonify({"status": "logged"})


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    print(f"[web] Listening on port {port}")
    app.run(host="0.0.0.0", port=port)


# ── Discord bot ───────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
bot_ref = bot

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

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    for cog in COGS:
        try:
            await bot.load_extension(cog)
            print(f"[cog] Loaded {cog}")
        except Exception as e:
            print(f"[cog] Failed to load {cog}: {e}")
    try:
        synced = await bot.tree.sync()
        print(f"[slash] Synced {len(synced)} commands")
    except Exception as e:
        print(f"[slash] Sync failed: {e}")


if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    bot.run(os.environ["DISCORD_TOKEN"])
